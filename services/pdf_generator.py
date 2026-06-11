import os
from weasyprint import HTML
from datetime import datetime

PDF_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
  
  * { margin: 0; padding: 0; box-sizing: border-box; }
  
  body {
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    color: #1a1a1a;
    padding: 40px;
    line-height: 1.6;
  }
  
  .header {
    border-bottom: 3px solid #1a3a5c;
    padding-bottom: 20px;
    margin-bottom: 30px;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }
  
  .logo {
    font-size: 22px;
    font-weight: 700;
    color: #1a3a5c;
    letter-spacing: -0.5px;
  }
  
  .logo span { color: #c9a84c; }
  
  .claim-meta {
    text-align: right;
    color: #555;
    font-size: 10px;
  }
  
  .claim-meta strong {
    display: block;
    font-size: 13px;
    color: #1a1a1a;
    margin-bottom: 4px;
  }
  
  .disclaimer {
    background: #f8f4e8;
    border-left: 4px solid #c9a84c;
    padding: 10px 14px;
    margin-bottom: 24px;
    font-size: 10px;
    color: #666;
  }
  
  .estimate-body {
    white-space: pre-wrap;
    font-size: 11px;
    line-height: 1.8;
  }
  
  .footer {
    margin-top: 40px;
    padding-top: 16px;
    border-top: 1px solid #ddd;
    font-size: 9px;
    color: #999;
    text-align: center;
  }
  
  h1, h2, h3 { color: #1a3a5c; margin: 16px 0 8px 0; }
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="logo">CITADEL <span>CLAIMS</span></div>
    <div style="font-size:10px; color:#888; margin-top:4px;">Professional Claims Estimating</div>
  </div>
  <div class="claim-meta">
    <strong>Claim ID: {claim_id}</strong>
    Generated: {date}<br>
    Adjuster Review Required Before Submission
  </div>
</div>

<div class="disclaimer">
  <strong>Review Notice:</strong> This estimate is prepared by Citadel Claims as a draft for licensed adjuster review. 
  The submitting adjuster is responsible for final accuracy and carrier submission. 
  If this estimate is rejected due to any content within this document, Citadel Claims will revise it free of charge, same-day priority.
</div>

<div class="estimate-body">{estimate_content}</div>

<div class="footer">
  Citadel Claims — Professional Insurance Estimating Service<br>
  This document is confidential and intended solely for the licensed adjuster named above.<br>
  Questions? Text your dedicated Citadel Claims number anytime.
</div>

</body>
</html>
"""


async def generate_pdf(claim_id: str, estimate_text: str, output_path: str) -> str:
    """Generate PDF from estimate text and save to output_path"""
    html_content = PDF_TEMPLATE.format(
        claim_id=claim_id,
        date=datetime.now().strftime("%B %d, %Y at %I:%M %p"),
        estimate_content=estimate_text
    )
    
    HTML(string=html_content).write_pdf(output_path)
    return output_path