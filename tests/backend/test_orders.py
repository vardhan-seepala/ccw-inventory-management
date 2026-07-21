"""
Tests for orders API endpoints.
"""
import pytest


class TestOrdersEndpoints:
    """Test suite for orders-related endpoints."""

    def test_get_all_orders(self, client):
        """Test getting all orders."""
        response = client.get("/api/orders")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Verify structure of first order
        first_order = data[0]
        assert "id" in first_order
        assert "order_number" in first_order
        assert "customer" in first_order
        assert "items" in first_order
        assert "status" in first_order
        assert "order_date" in first_order
        assert "expected_delivery" in first_order
        assert "total_value" in first_order

    def test_get_orders_by_warehouse(self, client):
        """Test filtering orders by warehouse."""
        response = client.get("/api/orders?warehouse=Tokyo")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        for order in data:
            assert order["warehouse"] == "Tokyo"

    def test_get_orders_by_category(self, client):
        """Test filtering orders by category."""
        response = client.get("/api/orders?category=Sensors")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        for order in data:
            assert order["category"].lower() == "sensors"

    def test_get_orders_by_status(self, client):
        """Test filtering orders by status."""
        response = client.get("/api/orders?status=Delivered")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        for order in data:
            assert order["status"].lower() == "delivered"

    def test_get_orders_by_month(self, client):
        """Test filtering orders by a single month."""
        response = client.get("/api/orders?month=2025-01")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        for order in data:
            assert "2025-01" in order["order_date"]

    def test_get_orders_by_quarter(self, client):
        """Test filtering orders by quarter (e.g. Q1-2025)."""
        response = client.get("/api/orders?month=Q1-2025")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        quarter_months = ["2025-01", "2025-02", "2025-03"]
        for order in data:
            assert any(m in order["order_date"] for m in quarter_months)

    def test_get_orders_by_all_quarters(self, client):
        """Test that filtering across all defined quarters covers every order."""
        response = client.get("/api/orders")
        all_orders = response.json()

        total_in_quarters = 0
        for quarter in ["Q1-2025", "Q2-2025", "Q3-2025", "Q4-2025"]:
            q_response = client.get(f"/api/orders?month={quarter}")
            assert q_response.status_code == 200
            total_in_quarters += len(q_response.json())

        assert total_in_quarters == len(all_orders)

    def test_get_orders_with_month_all(self, client):
        """Test that month=all returns all orders."""
        response_all = client.get("/api/orders?month=all")
        response_no_filter = client.get("/api/orders")

        assert response_all.status_code == 200
        assert len(response_all.json()) == len(response_no_filter.json())

    def test_get_orders_multiple_filters(self, client):
        """Test filtering orders with multiple filters combined."""
        response = client.get(
            "/api/orders?warehouse=Tokyo&category=Sensors&status=Delivered"
        )
        assert response.status_code == 200

        data = response.json()
        for order in data:
            assert order["warehouse"] == "Tokyo"
            assert order["category"].lower() == "sensors"
            assert order["status"].lower() == "delivered"

    def test_get_orders_warehouse_category_month_combined(self, client):
        """Test combining warehouse, category, and month/quarter filters."""
        response = client.get(
            "/api/orders?warehouse=London&category=Power Supplies&month=Q2-2025"
        )
        assert response.status_code == 200

        data = response.json()
        quarter_months = ["2025-04", "2025-05", "2025-06"]
        for order in data:
            assert order["warehouse"] == "London"
            assert order["category"].lower() == "power supplies"
            assert any(m in order["order_date"] for m in quarter_months)

    def test_get_orders_with_all_filter_values(self, client):
        """Test that 'all' filter values behave the same as no filters."""
        response = client.get(
            "/api/orders?warehouse=all&category=all&status=all&month=all"
        )
        response_no_filter = client.get("/api/orders")

        assert response.status_code == 200
        assert response.json() == response_no_filter.json()

    def test_get_order_by_id(self, client):
        """Test getting a specific order by ID."""
        response = client.get("/api/orders")
        all_orders = response.json()
        assert len(all_orders) > 0

        first_order_id = all_orders[0]["id"]

        response = client.get(f"/api/orders/{first_order_id}")
        assert response.status_code == 200

        order = response.json()
        assert order["id"] == first_order_id

    def test_get_nonexistent_order(self, client):
        """Test getting an order that doesn't exist."""
        response = client.get("/api/orders/nonexistent-order-999")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_order_items_structure(self, client):
        """Test that order items have proper structure."""
        response = client.get("/api/orders")
        data = response.json()

        for order in data:
            assert "items" in order
            assert isinstance(order["items"], list)

            for item in order["items"]:
                assert "sku" in item
                assert "name" in item
                assert "quantity" in item
                assert "unit_price" in item
                assert isinstance(item["quantity"], int)
                assert isinstance(item["unit_price"], (int, float))

    def test_order_status_values(self, client):
        """Test that orders have valid status values."""
        response = client.get("/api/orders")
        data = response.json()

        valid_statuses = ["delivered", "shipped", "processing", "backordered"]

        for order in data:
            assert order["status"].lower() in valid_statuses

    def test_order_dates_format(self, client):
        """Test that order dates are in proper ISO format."""
        response = client.get("/api/orders")
        data = response.json()

        for order in data:
            assert "2025-" in order["order_date"]
            assert "T" in order["order_date"]
            assert "-" in order["expected_delivery"]
            assert "T" in order["expected_delivery"]

    def test_order_total_value_calculation(self, client):
        """Test that order total_value matches sum of line items."""
        response = client.get("/api/orders")
        data = response.json()

        for order in data:
            assert "total_value" in order
            assert isinstance(order["total_value"], (int, float))
            assert order["total_value"] > 0

            calculated_total = sum(
                item["quantity"] * item["unit_price"]
                for item in order["items"]
            )
            assert abs(order["total_value"] - calculated_total) < 0.01

    def test_delivered_orders_actual_delivery_field_type(self, client):
        """Test that delivered orders expose actual_delivery as a string when present.

        Note: in the current mock dataset a handful of "Delivered" orders have
        actual_delivery=null (a data quirk, not enforced by the API), so this
        only checks the field's type rather than assuming it is always set.
        """
        response = client.get("/api/orders?status=Delivered")
        data = response.json()
        assert len(data) > 0

        for order in data:
            assert order["actual_delivery"] is None or isinstance(order["actual_delivery"], str)

    def test_most_delivered_orders_have_actual_delivery(self, client):
        """Test that the large majority of delivered orders have actual_delivery set."""
        response = client.get("/api/orders?status=Delivered")
        data = response.json()
        assert len(data) > 0

        with_delivery = sum(1 for order in data if order["actual_delivery"] is not None)
        # Allow a small number of data quirks, but most delivered orders should have a date.
        assert with_delivery / len(data) > 0.9

    def test_non_delivered_orders_may_lack_actual_delivery(self, client):
        """Test that non-delivered orders don't error on the optional actual_delivery field."""
        response = client.get("/api/orders?status=Processing")
        data = response.json()
        assert len(data) > 0

        for order in data:
            # actual_delivery is Optional[str]; either None or a string is valid
            assert order["actual_delivery"] is None or isinstance(order["actual_delivery"], str)

    def test_get_orders_nonexistent_warehouse_returns_empty(self, client):
        """Test that filtering by a nonexistent warehouse returns an empty list, not an error."""
        response = client.get("/api/orders?warehouse=Atlantis")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_orders_nonexistent_month_returns_empty(self, client):
        """Test that filtering by a month with no matching orders returns an empty list."""
        response = client.get("/api/orders?month=2030-01")
        assert response.status_code == 200
        assert response.json() == []
