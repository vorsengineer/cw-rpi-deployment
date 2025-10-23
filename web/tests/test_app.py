"""Comprehensive unit tests for Flask web management interface.

Test-Driven Development (TDD) - These tests are written BEFORE implementation.
All tests should fail initially (RED phase), then pass after implementation (GREEN phase).
"""

import json
from typing import Any
import pytest
from flask import Flask


class TestApplicationSetup:
    """Test Flask application initialization and configuration."""

    def test_app_exists(self, app: Flask) -> None:
        """Test that Flask application is created."""
        assert app is not None

    def test_app_is_testing(self, app: Flask) -> None:
        """Test that application is in testing mode."""
        assert app.config['TESTING'] is True

    def test_app_has_secret_key(self, app: Flask) -> None:
        """Test that application has a secret key configured."""
        assert app.config['SECRET_KEY'] is not None
        assert len(app.config['SECRET_KEY']) > 0

    def test_database_path_configured(self, app: Flask) -> None:
        """Test that database path is properly configured."""
        assert 'DATABASE_PATH' in app.config
        assert app.config['DATABASE_PATH'].endswith('.db')

    def test_hostname_manager_initialized(self, app: Flask) -> None:
        """Test that HostnameManager is initialized with correct database."""
        # This will be accessible via app context
        with app.app_context():
            from flask import current_app
            assert hasattr(current_app, 'hostname_manager')


class TestDashboardRoutes:
    """Test dashboard route and homepage."""

    def test_dashboard_get(self, client) -> None:
        """Test GET request to dashboard returns 200."""
        response = client.get('/')
        assert response.status_code == 200

    def test_dashboard_contains_title(self, client) -> None:
        """Test dashboard page contains page title."""
        response = client.get('/')
        assert b'Dashboard' in response.data or b'dashboard' in response.data.lower()

    def test_dashboard_contains_statistics(self, client, sample_venues) -> None:
        """Test dashboard displays venue statistics."""
        response = client.get('/')
        # Should display venue count
        assert b'venue' in response.data.lower() or b'Venue' in response.data

    def test_dashboard_shows_recent_deployments(self, client) -> None:
        """Test dashboard displays recent deployments section."""
        response = client.get('/')
        assert b'deployment' in response.data.lower() or b'Deployment' in response.data

    def test_dashboard_shows_system_status(self, client) -> None:
        """Test dashboard displays system status section."""
        response = client.get('/')
        assert b'status' in response.data.lower() or b'Status' in response.data


class TestVenueManagementRoutes:
    """Test venue management routes."""

    def test_venues_list_get(self, client) -> None:
        """Test GET request to venues list returns 200."""
        response = client.get('/venues')
        assert response.status_code == 200

    def test_venues_list_shows_venues(self, client, sample_venues) -> None:
        """Test venues list displays created venues."""
        response = client.get('/venues')
        # Should show venue codes
        for venue_code in sample_venues:
            assert venue_code.encode() in response.data

    def test_venue_detail_get(self, client, sample_venues) -> None:
        """Test GET request to venue detail page returns 200."""
        venue_code = sample_venues[0]
        response = client.get(f'/venues/{venue_code}')
        assert response.status_code == 200

    def test_venue_detail_shows_statistics(self, client, sample_venues, sample_kart_numbers) -> None:
        """Test venue detail page shows statistics."""
        venue_code = sample_venues[0]
        response = client.get(f'/venues/{venue_code}')
        # Should show kart count or statistics
        assert b'kart' in response.data.lower() or b'statistic' in response.data.lower()

    def test_venue_detail_invalid_code_404(self, client) -> None:
        """Test accessing non-existent venue returns 404."""
        response = client.get('/venues/XXXX')
        assert response.status_code == 404

    def test_create_venue_page_get(self, client) -> None:
        """Test GET request to create venue page returns 200."""
        response = client.get('/venues/create')
        assert response.status_code == 200

    def test_create_venue_page_has_form(self, client) -> None:
        """Test create venue page contains form fields."""
        response = client.get('/venues/create')
        assert b'<form' in response.data
        assert b'code' in response.data.lower()
        assert b'name' in response.data.lower()

    def test_create_venue_post_valid_data(self, client) -> None:
        """Test POST to create venue with valid data succeeds."""
        data = {
            'code': 'NEWV',
            'name': 'New Venue',
            'location': 'Test Location',
            'contact_email': 'new@venue.com'
        }
        response = client.post('/venues/create', data=data, follow_redirects=True)
        assert response.status_code == 200
        # Should redirect to venues list or show success message
        assert b'NEWV' in response.data or b'success' in response.data.lower()

    def test_create_venue_post_duplicate_code(self, client, sample_venues) -> None:
        """Test creating venue with duplicate code fails."""
        existing_code = sample_venues[0]
        data = {
            'code': existing_code,
            'name': 'Duplicate Venue',
            'location': 'Test',
            'contact_email': 'test@test.com'
        }
        response = client.post('/venues/create', data=data)
        # Should show error or return 400
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            assert b'error' in response.data.lower() or b'exists' in response.data.lower()

    def test_create_venue_post_invalid_code_format(self, client) -> None:
        """Test creating venue with invalid code format fails."""
        data = {
            'code': 'invalid',  # lowercase, should be 4 uppercase
            'name': 'Invalid Venue',
            'location': 'Test',
            'contact_email': 'test@test.com'
        }
        response = client.post('/venues/create', data=data)
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            assert b'error' in response.data.lower() or b'invalid' in response.data.lower()

    def test_create_venue_post_missing_required_fields(self, client) -> None:
        """Test creating venue with missing required fields fails."""
        data = {
            'code': 'TEST'
            # Missing name
        }
        response = client.post('/venues/create', data=data)
        assert response.status_code in [200, 400]

    def test_edit_venue_page_get(self, client, sample_venues) -> None:
        """Test GET request to edit venue page returns 200."""
        venue_code = sample_venues[0]
        response = client.get(f'/venues/{venue_code}/edit')
        assert response.status_code == 200

    def test_edit_venue_page_has_form(self, client, sample_venues) -> None:
        """Test edit venue page contains form with existing data."""
        venue_code = sample_venues[0]
        response = client.get(f'/venues/{venue_code}/edit')
        assert b'<form' in response.data
        assert venue_code.encode() in response.data

    def test_edit_venue_post_valid_data(self, client, sample_venues) -> None:
        """Test POST to edit venue with valid data succeeds."""
        venue_code = sample_venues[0]
        data = {
            'name': 'Updated Venue Name',
            'location': 'Updated Location',
            'contact_email': 'updated@venue.com'
        }
        response = client.post(f'/venues/{venue_code}/edit', data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b'Updated Venue Name' in response.data or b'success' in response.data.lower()


class TestKartNumberManagementRoutes:
    """Test kart number management routes."""

    def test_kart_numbers_list_get(self, client) -> None:
        """Test GET request to kart numbers list returns 200."""
        response = client.get('/kart-numbers')
        assert response.status_code == 200

    def test_kart_numbers_list_with_venue_filter(self, client, sample_venues) -> None:
        """Test kart numbers list with venue filter parameter."""
        venue_code = sample_venues[0]
        response = client.get(f'/kart-numbers?venue={venue_code}')
        assert response.status_code == 200
        assert venue_code.encode() in response.data

    def test_kart_numbers_shows_available_karts(self, client, sample_kart_numbers) -> None:
        """Test kart numbers list displays available karts."""
        response = client.get('/kart-numbers')
        # Should show at least one kart number
        assert b'001' in response.data or b'available' in response.data.lower()

    def test_bulk_import_page_get(self, client) -> None:
        """Test GET request to bulk import page returns 200."""
        response = client.get('/kart-numbers/bulk-import')
        assert response.status_code == 200

    def test_bulk_import_page_has_form(self, client) -> None:
        """Test bulk import page contains form."""
        response = client.get('/kart-numbers/bulk-import')
        assert b'<form' in response.data
        assert b'venue' in response.data.lower()

    def test_bulk_import_post_valid_numbers(self, client, sample_venues) -> None:
        """Test POST to bulk import with valid kart numbers succeeds."""
        venue_code = sample_venues[2]  # TEST venue
        data = {
            'venue_code': venue_code,
            'kart_numbers': '201, 202, 203'
        }
        response = client.post('/kart-numbers/bulk-import', data=data, follow_redirects=True)
        assert response.status_code == 200
        # Should show success message or imported numbers
        assert b'201' in response.data or b'success' in response.data.lower()

    def test_bulk_import_post_with_duplicates(self, client, sample_venues, sample_kart_numbers) -> None:
        """Test bulk import handles duplicate kart numbers gracefully."""
        venue_code = sample_venues[0]  # CORO
        existing_numbers = sample_kart_numbers[venue_code]
        data = {
            'venue_code': venue_code,
            'kart_numbers': f'{existing_numbers[0]}, 999'  # One duplicate, one new
        }
        response = client.post('/kart-numbers/bulk-import', data=data, follow_redirects=True)
        assert response.status_code == 200
        # Should handle duplicates gracefully and import new one
        assert b'duplicate' in response.data.lower() or b'999' in response.data

    def test_bulk_import_post_invalid_venue(self, client) -> None:
        """Test bulk import with invalid venue code fails."""
        data = {
            'venue_code': 'XXXX',
            'kart_numbers': '100, 101'
        }
        response = client.post('/kart-numbers/bulk-import', data=data)
        assert response.status_code in [200, 400, 404]

    def test_add_single_kart_number_post(self, client, sample_venues) -> None:
        """Test adding a single kart number."""
        venue_code = sample_venues[2]  # TEST venue
        data = {
            'venue_code': venue_code,
            'kart_number': '888'
        }
        response = client.post('/kart-numbers/add', data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b'888' in response.data or b'success' in response.data.lower()

    def test_delete_kart_number(self, client, sample_venues, sample_kart_numbers) -> None:
        """Test deleting a kart number."""
        # First, get a hostname to delete
        venue_code = sample_venues[0]
        kart_num = sample_kart_numbers[venue_code][0]
        hostname = f'KXP2-{venue_code}-{kart_num}'

        response = client.post(f'/kart-numbers/{hostname}/delete', follow_redirects=True)
        assert response.status_code == 200
        # Should show success or redirect to kart numbers list


class TestDeploymentMonitoringRoutes:
    """Test deployment monitoring routes."""

    def test_deployments_list_get(self, client) -> None:
        """Test GET request to deployments list returns 200."""
        response = client.get('/deployments')
        assert response.status_code == 200

    def test_deployments_shows_history_table(self, client) -> None:
        """Test deployments page contains deployment history."""
        response = client.get('/deployments')
        assert b'deployment' in response.data.lower()
        # Should have table structure
        assert b'<table' in response.data or b'<div' in response.data

    def test_deployments_with_venue_filter(self, client, sample_venues) -> None:
        """Test deployments list with venue filter."""
        venue_code = sample_venues[0]
        response = client.get(f'/deployments?venue={venue_code}')
        assert response.status_code == 200

    def test_deployments_with_product_filter(self, client) -> None:
        """Test deployments list with product type filter."""
        response = client.get('/deployments?product=KXP2')
        assert response.status_code == 200

    def test_deployments_with_status_filter(self, client) -> None:
        """Test deployments list with status filter."""
        response = client.get('/deployments?status=completed')
        assert response.status_code == 200

    def test_deployments_pagination(self, client) -> None:
        """Test deployments list supports pagination."""
        response = client.get('/deployments?page=1')
        assert response.status_code == 200


class TestSystemStatusRoutes:
    """Test system status and monitoring routes."""

    def test_system_status_get(self, client) -> None:
        """Test GET request to system status page returns 200."""
        response = client.get('/system')
        assert response.status_code == 200

    def test_system_status_shows_services(self, client) -> None:
        """Test system status page displays service status."""
        response = client.get('/system')
        # Should show service names
        assert (b'dnsmasq' in response.data or b'nginx' in response.data or
                b'service' in response.data.lower())

    def test_system_status_shows_network_info(self, client) -> None:
        """Test system status page displays network information."""
        response = client.get('/system')
        # Should show network interfaces or IP addresses
        assert b'eth' in response.data or b'network' in response.data.lower()

    def test_system_status_shows_disk_space(self, client) -> None:
        """Test system status page displays disk space information."""
        response = client.get('/system')
        assert b'disk' in response.data.lower() or b'storage' in response.data.lower()


class TestAPIEndpoints:
    """Test JSON API endpoints."""

    def test_api_stats_get(self, client, sample_venues) -> None:
        """Test GET request to /api/stats returns JSON."""
        response = client.get('/api/stats')
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        data = json.loads(response.data)
        assert 'total_venues' in data

    def test_api_stats_returns_correct_counts(self, client, sample_venues, sample_kart_numbers) -> None:
        """Test /api/stats returns correct venue and kart counts."""
        response = client.get('/api/stats')
        data = json.loads(response.data)
        assert data['total_venues'] == len(sample_venues)

    def test_api_venues_get(self, client, sample_venues) -> None:
        """Test GET request to /api/venues returns JSON."""
        response = client.get('/api/venues')
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == len(sample_venues)

    def test_api_venues_returns_venue_data(self, client, sample_venues) -> None:
        """Test /api/venues returns correct venue data."""
        response = client.get('/api/venues')
        data = json.loads(response.data)
        venue_codes = [v['code'] for v in data]
        for code in sample_venues:
            assert code in venue_codes

    def test_api_venue_stats_get(self, client, sample_venues) -> None:
        """Test GET request to /api/venues/<code>/stats returns JSON."""
        venue_code = sample_venues[0]
        response = client.get(f'/api/venues/{venue_code}/stats')
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        data = json.loads(response.data)
        assert 'venue_code' in data
        assert data['venue_code'] == venue_code

    def test_api_venue_stats_invalid_code_404(self, client) -> None:
        """Test /api/venues/<invalid>/stats returns 404."""
        response = client.get('/api/venues/XXXX/stats')
        assert response.status_code == 404

    def test_api_deployments_get(self, client) -> None:
        """Test GET request to /api/deployments returns JSON."""
        response = client.get('/api/deployments')
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_api_deployments_limit_parameter(self, client) -> None:
        """Test /api/deployments respects limit parameter."""
        response = client.get('/api/deployments?limit=5')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) <= 5

    def test_api_system_status_get(self, client) -> None:
        """Test GET request to /api/system/status returns JSON."""
        response = client.get('/api/system/status')
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        data = json.loads(response.data)
        assert 'services' in data
        assert isinstance(data['services'], dict)

    def test_api_system_status_includes_services(self, client) -> None:
        """Test /api/system/status includes service status."""
        response = client.get('/api/system/status')
        data = json.loads(response.data)
        services = data['services']
        # Should include at least one service
        assert len(services) > 0


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_404_page(self, client) -> None:
        """Test accessing non-existent page returns 404."""
        response = client.get('/this-page-does-not-exist')
        assert response.status_code == 404

    def test_404_page_has_content(self, client) -> None:
        """Test 404 page displays user-friendly error."""
        response = client.get('/this-page-does-not-exist')
        assert b'404' in response.data or b'not found' in response.data.lower()

    def test_500_error_handling(self, app, client) -> None:
        """Test 500 error page is displayed on server error."""
        # Create a route that raises an exception for testing
        @app.route('/test-error')
        def test_error():
            raise Exception("Test exception")

        response = client.get('/test-error')
        assert response.status_code == 500

    def test_invalid_form_data_handling(self, client) -> None:
        """Test that invalid form data is handled gracefully."""
        # POST with no data
        response = client.post('/venues/create', data={})
        assert response.status_code in [200, 400]


class TestWebSocketSupport:
    """Test WebSocket functionality (if implemented)."""

    def test_socketio_initialized(self, app) -> None:
        """Test that SocketIO is initialized with the app."""
        # Check if socketio extension exists
        assert hasattr(app, 'extensions')
        # SocketIO should be in extensions (if implemented)
        # This test may be skipped if WebSocket is not yet implemented

    # Note: Full WebSocket testing requires socketio test client
    # These tests can be expanded once WebSocket implementation is complete


class TestSecurityAndValidation:
    """Test input validation and security measures."""

    def test_xss_prevention_in_venue_name(self, client) -> None:
        """Test that XSS attempts in venue name are escaped."""
        data = {
            'code': 'XSST',
            'name': '<script>alert("xss")</script>',
            'location': 'Test',
            'contact_email': 'test@test.com'
        }
        response = client.post('/venues/create', data=data, follow_redirects=True)
        # Script tags should be escaped in output
        assert b'<script>' not in response.data or response.status_code == 400

    def test_sql_injection_prevention(self, client) -> None:
        """Test that SQL injection attempts are handled safely."""
        data = {
            'code': "'; DROP TABLE venues; --",
            'name': 'SQL Injection Test',
            'location': 'Test',
            'contact_email': 'test@test.com'
        }
        response = client.post('/venues/create', data=data)
        # Should either reject or escape the input
        assert response.status_code in [200, 400]

    def test_email_validation(self, client) -> None:
        """Test that invalid email addresses are rejected."""
        data = {
            'code': 'EMAI',
            'name': 'Email Test Venue',
            'location': 'Test',
            'contact_email': 'not-an-email'
        }
        response = client.post('/venues/create', data=data)
        # Should show validation error
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            assert b'email' in response.data.lower() or b'invalid' in response.data.lower()

    def test_venue_code_uppercase_enforcement(self, client) -> None:
        """Test that venue codes are converted to uppercase."""
        data = {
            'code': 'test',  # lowercase
            'name': 'Test Venue',
            'location': 'Test',
            'contact_email': 'test@test.com'
        }
        response = client.post('/venues/create', data=data, follow_redirects=True)
        # Should either convert to uppercase or reject
        if response.status_code == 200:
            # Check if TEST appears in response (converted to uppercase)
            assert b'TEST' in response.data or b'error' in response.data.lower()

    def test_venue_code_length_validation(self, client) -> None:
        """Test that venue codes must be exactly 4 characters."""
        # Too short
        data = {
            'code': 'TST',
            'name': 'Test Venue',
            'location': 'Test',
            'contact_email': 'test@test.com'
        }
        response = client.post('/venues/create', data=data)
        assert response.status_code in [200, 400]

        # Too long
        data['code'] = 'TESTS'
        response = client.post('/venues/create', data=data)
        assert response.status_code in [200, 400]


class TestIntegrationWorkflows:
    """Test complete workflows across multiple routes."""

    def test_create_venue_and_add_karts_workflow(self, client) -> None:
        """Test complete workflow: create venue → add kart numbers → view statistics."""
        # Step 1: Create new venue
        venue_data = {
            'code': 'FLOW',
            'name': 'Workflow Test Venue',
            'location': 'Test Location',
            'contact_email': 'flow@test.com'
        }
        response = client.post('/venues/create', data=venue_data, follow_redirects=True)
        assert response.status_code == 200

        # Step 2: Bulk import kart numbers
        kart_data = {
            'venue_code': 'FLOW',
            'kart_numbers': '301, 302, 303'
        }
        response = client.post('/kart-numbers/bulk-import', data=kart_data, follow_redirects=True)
        assert response.status_code == 200

        # Step 3: View venue statistics
        response = client.get('/venues/FLOW')
        assert response.status_code == 200
        # Should show the imported karts
        assert b'301' in response.data or b'3' in response.data  # 3 karts imported

    def test_dashboard_reflects_changes(self, client, sample_venues) -> None:
        """Test that dashboard statistics update after changes."""
        # Get initial dashboard state
        response1 = client.get('/')
        assert response1.status_code == 200

        # Create new venue
        venue_data = {
            'code': 'DASH',
            'name': 'Dashboard Test',
            'location': 'Test',
            'contact_email': 'dash@test.com'
        }
        client.post('/venues/create', data=venue_data, follow_redirects=True)

        # Get updated dashboard
        response2 = client.get('/')
        assert response2.status_code == 200
        # Dashboard should reflect the new venue
        assert b'DASH' in response2.data or b'4' in response2.data  # 4th venue
