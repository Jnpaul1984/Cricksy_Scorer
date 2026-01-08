"""Test that critical routes are properly registered in the FastAPI app."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_pdf_export_route_is_registered():
    """
    Verify that the PDF export endpoint is registered in the FastAPI app.
    
    This test catches route registration issues that cause 404 errors in CI.
    The route should be available at POST /api/coaches/plus/analysis-jobs/{job_id}/export-pdf
    """
    from backend.app import create_app
    
    # Create app (returns tuple of socketio wrapper and fastapi app)
    _, fastapi_app = create_app()
    
    # Collect all routes with their paths and methods
    routes_info = []
    for route in fastapi_app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes_info.append({
                'path': route.path,
                'methods': route.methods if route.methods else set(),
                'name': getattr(route, 'name', 'unknown')
            })
    
    # Find routes containing "export-pdf"
    export_pdf_routes = [
        r for r in routes_info 
        if 'export-pdf' in r['path']
    ]
    
    # Expected route
    expected_path = "/api/coaches/plus/analysis-jobs/{job_id}/export-pdf"
    expected_method = "POST"
    
    # Check if route exists
    matching_route = None
    for route in export_pdf_routes:
        if route['path'] == expected_path and expected_method in route['methods']:
            matching_route = route
            break
    
    # Detailed failure message
    if not matching_route:
        all_coach_routes = [
            r for r in routes_info 
            if '/api/coaches/plus/' in r['path']
        ]
        
        error_msg = f"\n{'='*80}\n"
        error_msg += f"ROUTE REGISTRATION FAILURE\n"
        error_msg += f"{'='*80}\n\n"
        error_msg += f"Expected route NOT FOUND:\n"
        error_msg += f"  Path:   {expected_path}\n"
        error_msg += f"  Method: {expected_method}\n\n"
        
        error_msg += f"Routes containing 'export-pdf' ({len(export_pdf_routes)}):\n"
        if export_pdf_routes:
            for r in export_pdf_routes:
                error_msg += f"  • {r['methods']} {r['path']} (name: {r['name']})\n"
        else:
            error_msg += f"  (none found)\n"
        
        error_msg += f"\nAll /api/coaches/plus/ routes ({len(all_coach_routes)}):\n"
        for r in sorted(all_coach_routes, key=lambda x: x['path']):
            error_msg += f"  • {r['methods']} {r['path']} (name: {r['name']})\n"
        
        error_msg += f"\nTotal routes registered: {len(routes_info)}\n"
        error_msg += f"{'='*80}\n"
        
        pytest.fail(error_msg)
    
    # Success - route is registered
    assert matching_route is not None
    assert expected_method in matching_route['methods']
    assert matching_route['path'] == expected_path


@pytest.mark.asyncio
async def test_coach_pro_plus_router_routes_registered():
    """Verify that all coach_pro_plus routes are registered."""
    from backend.app import create_app
    
    _, fastapi_app = create_app()
    
    # Get all routes
    all_paths = []
    for route in fastapi_app.routes:
        if hasattr(route, 'path'):
            all_paths.append(route.path)
    
    # Check for key coach_pro_plus routes (sampling)
    expected_routes = [
        "/api/coaches/plus/sessions",  # Create session
        "/api/coaches/plus/sessions/{session_id}",  # Get session
        "/api/coaches/plus/sessions/{session_id}/analysis-jobs",  # Create job
        "/api/coaches/plus/analysis-jobs/{job_id}",  # Get job
        "/api/coaches/plus/analysis-jobs/{job_id}/export-pdf",  # PDF export
    ]
    
    missing_routes = []
    for expected in expected_routes:
        if expected not in all_paths:
            missing_routes.append(expected)
    
    if missing_routes:
        error_msg = f"\nMissing coach_pro_plus routes:\n"
        for route in missing_routes:
            error_msg += f"  • {route}\n"
        error_msg += f"\nAll registered coach_pro_plus routes:\n"
        coach_routes = [p for p in all_paths if '/api/coaches/plus/' in p]
        for route in sorted(coach_routes):
            error_msg += f"  • {route}\n"
        pytest.fail(error_msg)
    
    assert len(missing_routes) == 0, f"Missing routes: {missing_routes}"
