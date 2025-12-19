from app.routers.reports import get_dashboard_stats
from app import models
from unittest.mock import MagicMock
from datetime import datetime

def test_dashboard_logic():
    # Mock DB Session
    db = MagicMock()
    
    # Mock date
    created_at = datetime.now()
    
    # Mock Reports
    report1 = MagicMock(spec=models.Report)
    report1.amount = 1000.0
    report1.created_at = created_at
    report1.category = "Food"
    report1.client_name = "Client A"
    report1.company_id = "test_company"
    
    report2 = MagicMock(spec=models.Report)
    report2.amount = 2000.0
    report2.created_at = created_at
    report2.category = "Transport"
    report2.client_name = "Client B"
    report2.company_id = "test_company"
    
    # Setup Query Mocks
    mock_query = db.query.return_value
    mock_filter = mock_query.filter.return_value
    
    # Mock count
    mock_filter.count.return_value = 2
    
    # Mock all() for full list
    mock_filter.all.return_value = [report1, report2]
    
    # Mock order_by().limit().all() for recent
    mock_filter.order_by.return_value.limit.return_value.all.return_value = [report1, report2]
    
    # Run Function
    stats = get_dashboard_stats(db, "test_company")
    
    # Assertions
    print("Keys found:", stats.keys())
    
    assert stats["total_reports"] == 2
    assert stats["total_spent"] == 3000.0
    
    # Check monthly stats
    assert len(stats["monthly_stats"]) == 1
    assert stats["monthly_stats"][0]["total"] == 3000.0
    
    # Check client stats
    print("Client Stats:", stats["client_stats"])
    assert len(stats["client_stats"]) == 2
    assert stats["client_stats"][0]["value"] == 2000.0 # Client B
    
    print("SUCCESS: Dashboard logic verified!")

if __name__ == "__main__":
    test_dashboard_logic()
