"""
Tests for reports API endpoints (quarterly and monthly-trends).
"""
import pytest


class TestQuarterlyReportsEndpoint:
    """Test suite for the /api/reports/quarterly endpoint."""

    def test_get_quarterly_reports(self, client):
        """Test getting quarterly reports."""
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        first_quarter = data[0]
        required_fields = [
            "quarter", "total_orders", "total_revenue",
            "delivered_orders", "avg_order_value", "fulfillment_rate"
        ]
        for field in required_fields:
            assert field in first_quarter, f"Missing field: {field}"

    def test_quarterly_reports_sorted_by_quarter(self, client):
        """Test that quarters are returned in ascending order."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        quarters = [q["quarter"] for q in data]
        assert quarters == sorted(quarters)

    def test_quarterly_reports_covers_all_quarters(self, client):
        """Test that all four 2025 quarters are present given the dataset spans the full year."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        quarters = {q["quarter"] for q in data}
        assert quarters == {"Q1-2025", "Q2-2025", "Q3-2025", "Q4-2025"}

    def test_quarterly_total_orders_matches_raw_orders(self, client):
        """Test that each quarter's total_orders matches the count of orders filtered by that quarter."""
        response = client.get("/api/reports/quarterly")
        quarterly_data = response.json()

        for q in quarterly_data:
            orders_response = client.get(f"/api/orders?month={q['quarter']}")
            raw_orders = orders_response.json()
            assert q["total_orders"] == len(raw_orders), \
                f"{q['quarter']}: expected {len(raw_orders)}, got {q['total_orders']}"

    def test_quarterly_total_orders_sum_matches_all_orders(self, client):
        """Test that summing total_orders across quarters equals the full order count."""
        response = client.get("/api/reports/quarterly")
        quarterly_data = response.json()

        all_orders_response = client.get("/api/orders")
        all_orders = all_orders_response.json()

        total = sum(q["total_orders"] for q in quarterly_data)
        assert total == len(all_orders)

    def test_quarterly_revenue_matches_raw_orders(self, client):
        """Test that total_revenue for a quarter matches the sum of total_value for orders in that quarter."""
        response = client.get("/api/reports/quarterly")
        quarterly_data = response.json()

        for q in quarterly_data:
            orders_response = client.get(f"/api/orders?month={q['quarter']}")
            raw_orders = orders_response.json()
            expected_revenue = sum(o["total_value"] for o in raw_orders)
            assert abs(q["total_revenue"] - expected_revenue) < 0.01

    def test_quarterly_delivered_orders_matches_raw_orders(self, client):
        """Test that delivered_orders count matches Delivered-status orders in that quarter."""
        response = client.get("/api/reports/quarterly")
        quarterly_data = response.json()

        for q in quarterly_data:
            orders_response = client.get(f"/api/orders?month={q['quarter']}&status=Delivered")
            delivered_orders = orders_response.json()
            assert q["delivered_orders"] == len(delivered_orders)

    def test_quarterly_avg_order_value_calculation(self, client):
        """Test that avg_order_value is total_revenue / total_orders."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        for q in data:
            if q["total_orders"] > 0:
                expected_avg = round(q["total_revenue"] / q["total_orders"], 2)
                assert abs(q["avg_order_value"] - expected_avg) < 0.01

    def test_quarterly_fulfillment_rate_calculation(self, client):
        """Test that fulfillment_rate is delivered_orders / total_orders * 100."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        for q in data:
            if q["total_orders"] > 0:
                expected_rate = round((q["delivered_orders"] / q["total_orders"]) * 100, 1)
                assert abs(q["fulfillment_rate"] - expected_rate) < 0.1

    def test_quarterly_reports_non_negative_values(self, client):
        """Test that all numeric quarterly fields are non-negative."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        for q in data:
            assert q["total_orders"] >= 0
            assert q["total_revenue"] >= 0
            assert q["delivered_orders"] >= 0
            assert q["avg_order_value"] >= 0
            assert q["fulfillment_rate"] >= 0
            assert q["delivered_orders"] <= q["total_orders"]

    def test_quarterly_reports_filtered_by_warehouse_matches_raw_orders(self, client):
        """Test that filtering by warehouse narrows quarterly totals consistently with /api/orders."""
        orders_response = client.get("/api/orders")
        warehouses = {o["warehouse"] for o in orders_response.json() if o.get("warehouse")}
        assert warehouses, "Expected at least one warehouse in the dataset"
        warehouse = sorted(warehouses)[0]

        response = client.get(f"/api/reports/quarterly?warehouse={warehouse}")
        assert response.status_code == 200
        quarterly_data = response.json()

        for q in quarterly_data:
            raw_orders_response = client.get(f"/api/orders?month={q['quarter']}&warehouse={warehouse}")
            raw_orders = raw_orders_response.json()
            assert q["total_orders"] == len(raw_orders)

    def test_quarterly_reports_filtered_by_status_matches_raw_orders(self, client):
        """Test that filtering by status narrows quarterly totals consistently with /api/orders."""
        response = client.get("/api/reports/quarterly?status=Delivered")
        assert response.status_code == 200
        quarterly_data = response.json()

        for q in quarterly_data:
            raw_orders_response = client.get(f"/api/orders?month={q['quarter']}&status=Delivered")
            raw_orders = raw_orders_response.json()
            assert q["total_orders"] == len(raw_orders)
            # Filtering to only Delivered orders means fulfillment rate should be 100%
            assert q["fulfillment_rate"] == 100.0

    def test_quarterly_reports_filtered_by_month_scopes_to_single_quarter(self, client):
        """Test that filtering by a single month only returns that month's quarter."""
        response = client.get("/api/reports/quarterly?month=2025-01")
        assert response.status_code == 200
        data = response.json()

        quarters = {q["quarter"] for q in data}
        assert quarters == {"Q1-2025"}

    def test_quarterly_reports_filtered_by_category_no_error(self, client):
        """Test that filtering by category returns a valid, well-formed response."""
        orders_response = client.get("/api/orders")
        categories = {o["category"] for o in orders_response.json() if o.get("category")}
        assert categories, "Expected at least one category in the dataset"
        category = sorted(categories)[0]

        response = client.get(f"/api/reports/quarterly?category={category}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for q in data:
            assert q["total_orders"] >= 0


class TestMonthlyTrendsEndpoint:
    """Test suite for the /api/reports/monthly-trends endpoint."""

    def test_get_monthly_trends(self, client):
        """Test getting monthly trends."""
        response = client.get("/api/reports/monthly-trends")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        first_month = data[0]
        required_fields = ["month", "order_count", "revenue", "delivered_count"]
        for field in required_fields:
            assert field in first_month, f"Missing field: {field}"

    def test_monthly_trends_sorted_by_month(self, client):
        """Test that months are returned in ascending order."""
        response = client.get("/api/reports/monthly-trends")
        data = response.json()

        months = [m["month"] for m in data]
        assert months == sorted(months)

    def test_monthly_trends_covers_all_months(self, client):
        """Test that all twelve months of 2025 are present."""
        response = client.get("/api/reports/monthly-trends")
        data = response.json()

        months = {m["month"] for m in data}
        expected_months = {f"2025-{i:02d}" for i in range(1, 13)}
        assert months == expected_months

    def test_monthly_order_count_matches_raw_orders(self, client):
        """Test that each month's order_count matches the count of orders filtered by that month."""
        response = client.get("/api/reports/monthly-trends")
        monthly_data = response.json()

        for m in monthly_data:
            orders_response = client.get(f"/api/orders?month={m['month']}")
            raw_orders = orders_response.json()
            assert m["order_count"] == len(raw_orders), \
                f"{m['month']}: expected {len(raw_orders)}, got {m['order_count']}"

    def test_monthly_order_count_sum_matches_all_orders(self, client):
        """Test that summing order_count across months equals the full order count."""
        response = client.get("/api/reports/monthly-trends")
        monthly_data = response.json()

        all_orders_response = client.get("/api/orders")
        all_orders = all_orders_response.json()

        total = sum(m["order_count"] for m in monthly_data)
        assert total == len(all_orders)

    def test_monthly_revenue_matches_raw_orders(self, client):
        """Test that revenue for a month matches the sum of total_value for orders in that month."""
        response = client.get("/api/reports/monthly-trends")
        monthly_data = response.json()

        for m in monthly_data:
            orders_response = client.get(f"/api/orders?month={m['month']}")
            raw_orders = orders_response.json()
            expected_revenue = sum(o["total_value"] for o in raw_orders)
            assert abs(m["revenue"] - expected_revenue) < 0.01

    def test_monthly_delivered_count_matches_raw_orders(self, client):
        """Test that delivered_count matches Delivered-status orders in that month."""
        response = client.get("/api/reports/monthly-trends")
        monthly_data = response.json()

        for m in monthly_data:
            orders_response = client.get(f"/api/orders?month={m['month']}&status=Delivered")
            delivered_orders = orders_response.json()
            assert m["delivered_count"] == len(delivered_orders)

    def test_monthly_trends_non_negative_values(self, client):
        """Test that all numeric monthly fields are non-negative and internally consistent."""
        response = client.get("/api/reports/monthly-trends")
        data = response.json()

        for m in data:
            assert m["order_count"] >= 0
            assert m["revenue"] >= 0
            assert m["delivered_count"] >= 0
            assert m["delivered_count"] <= m["order_count"]

    def test_monthly_trends_and_quarterly_reports_totals_agree(self, client):
        """Test that monthly-trends and quarterly totals reconcile to the same grand totals."""
        monthly_response = client.get("/api/reports/monthly-trends")
        monthly_data = monthly_response.json()

        quarterly_response = client.get("/api/reports/quarterly")
        quarterly_data = quarterly_response.json()

        monthly_total_orders = sum(m["order_count"] for m in monthly_data)
        quarterly_total_orders = sum(q["total_orders"] for q in quarterly_data)
        assert monthly_total_orders == quarterly_total_orders

        monthly_total_revenue = sum(m["revenue"] for m in monthly_data)
        quarterly_total_revenue = sum(q["total_revenue"] for q in quarterly_data)
        assert abs(monthly_total_revenue - quarterly_total_revenue) < 0.01

    def test_monthly_trends_filtered_by_warehouse_matches_raw_orders(self, client):
        """Test that filtering by warehouse narrows monthly totals consistently with /api/orders."""
        orders_response = client.get("/api/orders")
        warehouses = {o["warehouse"] for o in orders_response.json() if o.get("warehouse")}
        assert warehouses, "Expected at least one warehouse in the dataset"
        warehouse = sorted(warehouses)[0]

        response = client.get(f"/api/reports/monthly-trends?warehouse={warehouse}")
        assert response.status_code == 200
        monthly_data = response.json()

        for m in monthly_data:
            raw_orders_response = client.get(f"/api/orders?month={m['month']}&warehouse={warehouse}")
            raw_orders = raw_orders_response.json()
            assert m["order_count"] == len(raw_orders)

    def test_monthly_trends_filtered_by_status_matches_raw_orders(self, client):
        """Test that filtering by status narrows monthly totals consistently with /api/orders."""
        response = client.get("/api/reports/monthly-trends?status=Delivered")
        assert response.status_code == 200
        monthly_data = response.json()

        for m in monthly_data:
            raw_orders_response = client.get(f"/api/orders?month={m['month']}&status=Delivered")
            raw_orders = raw_orders_response.json()
            assert m["order_count"] == len(raw_orders)
            # Filtering to only Delivered orders means delivered_count == order_count
            assert m["delivered_count"] == m["order_count"]

    def test_monthly_trends_filtered_by_month_scopes_to_single_month(self, client):
        """Test that filtering by a single month only returns that month."""
        response = client.get("/api/reports/monthly-trends?month=2025-01")
        assert response.status_code == 200
        data = response.json()

        months = {m["month"] for m in data}
        assert months == {"2025-01"}

    def test_monthly_trends_filtered_by_category_no_error(self, client):
        """Test that filtering by category returns a valid, well-formed response."""
        orders_response = client.get("/api/orders")
        categories = {o["category"] for o in orders_response.json() if o.get("category")}
        assert categories, "Expected at least one category in the dataset"
        category = sorted(categories)[0]

        response = client.get(f"/api/reports/monthly-trends?category={category}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for m in data:
            assert m["order_count"] >= 0
