"""
Tests for restocking recommendation API endpoints.
"""
import pytest


class TestRestockingEndpoints:
    """Test suite for budget-based restocking recommendation endpoint."""

    def test_get_recommendations_basic(self, client):
        """Test getting restocking recommendations with a budget returns the expected shape."""
        response = client.get("/api/restocking/recommendations?budget=20000")
        assert response.status_code == 200

        data = response.json()
        assert "summary" in data
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)

        summary = data["summary"]
        for field in ["budget", "total_allocated", "remaining_budget", "items_recommended"]:
            assert field in summary

    def test_recommendation_structure(self, client):
        """Test that each recommendation has the full expected field set."""
        response = client.get("/api/restocking/recommendations?budget=20000")
        data = response.json()
        assert len(data["recommendations"]) > 0

        first = data["recommendations"][0]
        expected_fields = [
            "sku", "name", "category", "warehouse", "quantity_on_hand",
            "reorder_point", "demand_score", "priority_score",
            "recommended_quantity", "allocated_quantity", "unit_cost", "line_cost"
        ]
        for field in expected_fields:
            assert field in first

    def test_budget_never_exceeded(self, client):
        """Test that total allocated spend never exceeds the given budget, for several budgets."""
        for budget in [500, 5000, 20000, 100000]:
            response = client.get(f"/api/restocking/recommendations?budget={budget}")
            assert response.status_code == 200

            data = response.json()
            summary = data["summary"]

            assert summary["total_allocated"] <= summary["budget"]
            assert summary["remaining_budget"] >= 0

            calculated_total = sum(r["line_cost"] for r in data["recommendations"])
            assert abs(calculated_total - summary["total_allocated"]) < 0.01

    def test_ranking_order_by_priority(self, client):
        """Test that recommendations are sorted descending by priority_score."""
        response = client.get("/api/restocking/recommendations?budget=100000")
        data = response.json()
        recommendations = data["recommendations"]
        assert len(recommendations) > 1

        scores = [r["priority_score"] for r in recommendations]
        assert scores == sorted(scores, reverse=True)

    def test_recommended_quantity_targets_double_reorder_point(self, client):
        """Test that recommended_quantity brings stock toward 2x reorder_point, capped by budget for allocation."""
        response = client.get("/api/restocking/recommendations?budget=1000000")
        data = response.json()
        assert len(data["recommendations"]) > 0

        for r in data["recommendations"]:
            assert r["quantity_on_hand"] + r["recommended_quantity"] >= 2 * r["reorder_point"]
            assert r["allocated_quantity"] <= r["recommended_quantity"]

    def test_missing_budget_returns_422(self, client):
        """Test that omitting the required budget query param returns a validation error."""
        response = client.get("/api/restocking/recommendations")
        assert response.status_code == 422

    def test_budget_zero(self, client):
        """Test that a zero budget returns no recommendations."""
        response = client.get("/api/restocking/recommendations?budget=0")
        assert response.status_code == 200

        data = response.json()
        assert data["recommendations"] == []
        assert data["summary"]["total_allocated"] == 0
        assert data["summary"]["remaining_budget"] == 0
        assert data["summary"]["items_recommended"] == 0

    def test_budget_smaller_than_cheapest_item(self, client):
        """Test that a budget too small to afford any single unit returns no recommendations."""
        response = client.get("/api/restocking/recommendations?budget=1")
        assert response.status_code == 200

        data = response.json()
        assert data["recommendations"] == []
        assert data["summary"]["remaining_budget"] == 1

    def test_negative_budget_rejected(self, client):
        """Test that a negative budget is rejected with a 400 error."""
        response = client.get("/api/restocking/recommendations?budget=-100")
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data

    def test_warehouse_filter_narrows_results(self, client):
        """Test that filtering by warehouse only returns recommendations for that warehouse."""
        response = client.get("/api/restocking/recommendations?budget=100000&warehouse=Tokyo")
        assert response.status_code == 200

        data = response.json()
        for r in data["recommendations"]:
            assert r["warehouse"] == "Tokyo"

    def test_category_filter_narrows_results(self, client):
        """Test that filtering by category only returns recommendations for that category."""
        response = client.get("/api/restocking/recommendations?budget=100000&category=Sensors")
        assert response.status_code == 200

        data = response.json()
        for r in data["recommendations"]:
            assert r["category"].lower() == "sensors"

    def test_well_stocked_items_never_recommended(self, client):
        """Test that items already at or above 2x reorder_point are excluded, regardless of budget size."""
        response = client.get("/api/restocking/recommendations?budget=10000000")
        assert response.status_code == 200

        data = response.json()
        assert len(data["recommendations"]) > 0

        for r in data["recommendations"]:
            assert r["quantity_on_hand"] < 2 * r["reorder_point"]
