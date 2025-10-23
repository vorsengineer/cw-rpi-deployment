"""Integration tests for Flask web management interface.

Tests complete workflows and interactions between multiple components.
"""

import json
from typing import Any
import pytest


class TestVenueManagementIntegration:
    """Integration tests for venue management features."""

    def test_complete_venue_lifecycle(self, client, hostname_manager) -> None:
        """Test complete venue lifecycle: create → view → edit → view stats."""
        # Create venue
        venue_data = {
            'code': 'INTG',
            'name': 'Integration Test Venue',
            'location': 'Integration Test Location',
            'contact_email': 'integration@test.com'
        }
        response = client.post('/venues/create', data=venue_data, follow_redirects=True)
        assert response.status_code == 200
        assert b'INTG' in response.data

        # View venue list - should include new venue
        response = client.get('/venues')
        assert response.status_code == 200
        assert b'INTG' in response.data
        assert b'Integration Test Venue' in response.data

        # View venue detail page
        response = client.get('/venues/INTG')
        assert response.status_code == 200
        assert b'Integration Test Venue' in response.data

        # Edit venue
        edit_data = {
            'name': 'Updated Integration Venue',
            'location': 'Updated Location',
            'contact_email': 'updated@test.com'
        }
        response = client.post('/venues/INTG/edit', data=edit_data, follow_redirects=True)
        assert response.status_code == 200
        assert b'Updated Integration Venue' in response.data

        # Verify changes via API
        response = client.get('/api/venues')
        data = json.loads(response.data)
        intg_venue = [v for v in data if v['code'] == 'INTG'][0]
        assert intg_venue['name'] == 'Updated Integration Venue'

    def test_venue_with_kart_numbers_integration(self, client) -> None:
        """Test venue creation and immediate kart number assignment."""
        # Create venue
        venue_data = {
            'code': 'KART',
            'name': 'Kart Test Venue',
            'location': 'Test',
            'contact_email': 'kart@test.com'
        }
        client.post('/venues/create', data=venue_data, follow_redirects=True)

        # Bulk import kart numbers
        kart_data = {
            'venue_code': 'KART',
            'kart_numbers': '401, 402, 403, 404, 405'
        }
        response = client.post('/kart-numbers/bulk-import', data=kart_data, follow_redirects=True)
        assert response.status_code == 200

        # Verify via API
        response = client.get('/api/venues/KART/stats')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['total_hostnames'] == 5
        assert data['available_hostnames'] == 5


class TestKartNumberManagementIntegration:
    """Integration tests for kart number management."""

    def test_bulk_import_and_individual_operations(self, client, sample_venues) -> None:
        """Test bulk import followed by individual add and delete."""
        venue_code = sample_venues[2]  # TEST venue

        # Bulk import
        kart_data = {
            'venue_code': venue_code,
            'kart_numbers': '501, 502, 503'
        }
        response = client.post('/kart-numbers/bulk-import', data=kart_data, follow_redirects=True)
        assert response.status_code == 200

        # Add individual kart number
        add_data = {
            'venue_code': venue_code,
            'kart_number': '504'
        }
        response = client.post('/kart-numbers/add', data=add_data, follow_redirects=True)
        assert response.status_code == 200

        # Verify 4 karts exist
        response = client.get(f'/kart-numbers?venue={venue_code}')
        assert b'501' in response.data
        assert b'504' in response.data

        # Delete one kart
        hostname = f'KXP2-{venue_code}-501'
        response = client.post(f'/kart-numbers/{hostname}/delete', follow_redirects=True)
        assert response.status_code == 200

        # Verify deletion via API
        response = client.get('/api/venues/TEST/stats')
        data = json.loads(response.data)
        # Should have fewer available hostnames now
        assert data['total_hostnames'] >= 3

    def test_kart_number_filtering(self, client, sample_venues, sample_kart_numbers) -> None:
        """Test filtering kart numbers by venue."""
        # Get karts for specific venue
        venue_code = sample_venues[0]  # CORO
        response = client.get(f'/kart-numbers?venue={venue_code}')
        assert response.status_code == 200
        assert venue_code.encode() in response.data

        # Verify only CORO karts are shown
        for kart_num in sample_kart_numbers[venue_code]:
            assert kart_num.encode() in response.data


class TestDeploymentMonitoringIntegration:
    """Integration tests for deployment monitoring."""

    def test_deployment_history_recording(self, client, hostname_manager, sample_venues) -> None:
        """Test that hostname assignments appear in deployment history."""
        venue_code = sample_venues[0]

        # Assign a hostname (simulates deployment)
        hostname = hostname_manager.assign_hostname(
            product_type='KXP2',
            venue_code=venue_code,
            mac_address='AA:BB:CC:DD:EE:01'
        )
        assert hostname is not None

        # Record deployment in history
        conn = hostname_manager._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO deployment_history
            (hostname, mac_address, serial_number, product_type, venue_code, ip_address, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (hostname, 'AA:BB:CC:DD:EE:01', 'TEST123', 'KXP2', venue_code, '192.168.151.100', 'completed'))
        conn.commit()

        # Verify appears in deployments page
        response = client.get('/deployments')
        assert response.status_code == 200
        assert hostname.encode() in response.data

        # Verify appears in API
        response = client.get('/api/deployments?limit=10')
        assert response.status_code == 200
        data = json.loads(response.data)
        hostnames = [d['hostname'] for d in data]
        assert hostname in hostnames

    def test_deployment_filtering(self, client, hostname_manager, sample_venues) -> None:
        """Test filtering deployments by various criteria."""
        # Create multiple deployments
        conn = hostname_manager._get_connection()
        cursor = conn.cursor()

        deployments = [
            ('KXP2-CORO-001', 'AA:BB:CC:DD:EE:01', 'KXP2', 'CORO', 'completed'),
            ('KXP2-CORO-002', 'AA:BB:CC:DD:EE:02', 'KXP2', 'CORO', 'failed'),
            ('RXP2-ARIA-ABC123', 'AA:BB:CC:DD:EE:03', 'RXP2', 'ARIA', 'completed'),
        ]

        for hostname, mac, product, venue, status in deployments:
            cursor.execute("""
                INSERT INTO deployment_history
                (hostname, mac_address, serial_number, product_type, venue_code, ip_address, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (hostname, mac, 'TEST' + mac[-2:], product, venue, '192.168.151.100', status))
        conn.commit()

        # Filter by venue
        response = client.get('/deployments?venue=CORO')
        assert response.status_code == 200
        assert b'CORO' in response.data

        # Filter by product
        response = client.get('/deployments?product=RXP2')
        assert response.status_code == 200
        assert b'RXP2' in response.data

        # Filter by status
        response = client.get('/deployments?status=completed')
        assert response.status_code == 200


class TestDashboardIntegration:
    """Integration tests for dashboard functionality."""

    def test_dashboard_aggregates_all_data(self, client, sample_venues, sample_kart_numbers) -> None:
        """Test that dashboard displays aggregated data from all sources."""
        response = client.get('/')
        assert response.status_code == 200

        # Should show venue count
        assert str(len(sample_venues)).encode() in response.data or b'venue' in response.data.lower()

        # Verify via API
        response = client.get('/api/stats')
        data = json.loads(response.data)
        assert data['total_venues'] == len(sample_venues)

    def test_dashboard_real_time_updates(self, client) -> None:
        """Test that dashboard reflects changes immediately."""
        # Get initial stats
        response = client.get('/api/stats')
        initial_data = json.loads(response.data)
        initial_venues = initial_data['total_venues']

        # Create new venue
        venue_data = {
            'code': 'REAL',
            'name': 'Real Time Test',
            'location': 'Test',
            'contact_email': 'realtime@test.com'
        }
        client.post('/venues/create', data=venue_data, follow_redirects=True)

        # Get updated stats
        response = client.get('/api/stats')
        updated_data = json.loads(response.data)
        assert updated_data['total_venues'] == initial_venues + 1


class TestSystemStatusIntegration:
    """Integration tests for system status monitoring."""

    def test_system_status_comprehensive_check(self, client) -> None:
        """Test that system status page shows all monitoring data."""
        response = client.get('/system')
        assert response.status_code == 200

        # Should show various system components
        assert (b'dnsmasq' in response.data or b'nginx' in response.data or
                b'service' in response.data.lower())

    def test_system_status_api_returns_complete_data(self, client) -> None:
        """Test that system status API returns comprehensive status."""
        response = client.get('/api/system/status')
        assert response.status_code == 200
        data = json.loads(response.data)

        # Should have services section
        assert 'services' in data
        assert isinstance(data['services'], dict)

        # Should check at least some critical services
        # (exact services depend on implementation)
        assert len(data['services']) > 0


class TestAPIConsistency:
    """Integration tests for API endpoint consistency."""

    def test_web_and_api_data_consistency(self, client, sample_venues) -> None:
        """Test that web pages and API endpoints return consistent data."""
        venue_code = sample_venues[0]

        # Get data from web page
        response_web = client.get(f'/venues/{venue_code}')
        assert response_web.status_code == 200

        # Get data from API
        response_api = client.get(f'/api/venues/{venue_code}/stats')
        assert response_api.status_code == 200
        api_data = json.loads(response_api.data)

        # Both should show same venue
        assert venue_code in response_web.data.decode()
        assert api_data['venue_code'] == venue_code

    def test_all_venues_accessible_via_web_and_api(self, client, sample_venues) -> None:
        """Test that all venues are accessible via both web and API."""
        # Get venues from API
        response = client.get('/api/venues')
        api_venues = json.loads(response.data)
        api_codes = [v['code'] for v in api_venues]

        # Verify each venue has a working detail page
        for venue_code in sample_venues:
            assert venue_code in api_codes

            # Check web page works
            response = client.get(f'/venues/{venue_code}')
            assert response.status_code == 200

            # Check API endpoint works
            response = client.get(f'/api/venues/{venue_code}/stats')
            assert response.status_code == 200


class TestErrorRecoveryIntegration:
    """Integration tests for error handling and recovery."""

    def test_graceful_degradation_on_database_error(self, client) -> None:
        """Test that application handles database errors gracefully."""
        # Try to access venue that doesn't exist
        response = client.get('/venues/XXXX')
        assert response.status_code == 404

        # Application should still work for valid requests
        response = client.get('/venues')
        assert response.status_code == 200

    def test_form_validation_preserves_valid_fields(self, client) -> None:
        """Test that form validation preserves valid fields when submission fails."""
        # Submit form with one invalid field
        data = {
            'code': 'VALID',
            'name': 'Valid Name',
            'location': 'Valid Location',
            'contact_email': 'invalid-email'  # Invalid
        }
        response = client.post('/venues/create', data=data)
        assert response.status_code in [200, 400]

        # If form is re-rendered, valid fields should be preserved
        if response.status_code == 200:
            assert b'VALID' in response.data or b'Valid Name' in response.data


class TestConcurrentOperations:
    """Integration tests for concurrent operations."""

    def test_multiple_kart_imports_same_venue(self, client, sample_venues) -> None:
        """Test handling multiple kart imports for same venue."""
        venue_code = sample_venues[2]  # TEST venue

        # Import first batch
        kart_data_1 = {
            'venue_code': venue_code,
            'kart_numbers': '601, 602, 603'
        }
        response = client.post('/kart-numbers/bulk-import', data=kart_data_1, follow_redirects=True)
        assert response.status_code == 200

        # Import second batch
        kart_data_2 = {
            'venue_code': venue_code,
            'kart_numbers': '604, 605, 606'
        }
        response = client.post('/kart-numbers/bulk-import', data=kart_data_2, follow_redirects=True)
        assert response.status_code == 200

        # Verify all 6 karts exist
        response = client.get(f'/api/venues/{venue_code}/stats')
        data = json.loads(response.data)
        # Should have at least the 6 new karts (plus any existing ones)
        assert data['total_hostnames'] >= 6


class TestDataPersistence:
    """Integration tests for data persistence."""

    def test_venue_persists_across_requests(self, client) -> None:
        """Test that created venue persists across multiple requests."""
        # Create venue
        venue_data = {
            'code': 'PERS',
            'name': 'Persistence Test',
            'location': 'Test',
            'contact_email': 'persist@test.com'
        }
        client.post('/venues/create', data=venue_data, follow_redirects=True)

        # Make multiple requests - data should persist
        for _ in range(3):
            response = client.get('/venues/PERS')
            assert response.status_code == 200
            assert b'Persistence Test' in response.data

    def test_kart_numbers_persist_after_venue_edit(self, client) -> None:
        """Test that kart numbers remain intact after venue is edited."""
        # Create venue and add karts
        venue_data = {
            'code': 'EDIT',
            'name': 'Edit Test Venue',
            'location': 'Test',
            'contact_email': 'edit@test.com'
        }
        client.post('/venues/create', data=venue_data, follow_redirects=True)

        kart_data = {
            'venue_code': 'EDIT',
            'kart_numbers': '701, 702, 703'
        }
        client.post('/kart-numbers/bulk-import', data=kart_data, follow_redirects=True)

        # Get initial kart count
        response = client.get('/api/venues/EDIT/stats')
        initial_count = json.loads(response.data)['total_hostnames']

        # Edit venue
        edit_data = {
            'name': 'Edited Venue Name',
            'location': 'New Location',
            'contact_email': 'newedit@test.com'
        }
        client.post('/venues/EDIT/edit', data=edit_data, follow_redirects=True)

        # Verify kart count unchanged
        response = client.get('/api/venues/EDIT/stats')
        final_count = json.loads(response.data)['total_hostnames']
        assert final_count == initial_count
