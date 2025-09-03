import os
from pathlib import Path

def setup_directory_structure():
    """Create the required directory structure and sample files"""
    
    # Create data directories
    Path("./data/plans").mkdir(parents=True, exist_ok=True)
    Path("./data/traces").mkdir(parents=True, exist_ok=True)
    
    # Create context directories
    Path("./contexts/schools/status").mkdir(parents=True, exist_ok=True)
    Path("./contexts/companies/status").mkdir(parents=True, exist_ok=True)
    
    # Create sample context files
    context_files = {
        "./contexts/schools/status/new.txt": """
For new school contacts:
- Introduce yourself and your organization
- Highlight key benefits for educational institutions
- Offer a demo or meeting
- Keep tone professional but approachable
- Mention any education-specific features or discounts
        """,
        
        "./contexts/schools/status/meeting.txt": """
For schools after initial meeting:
- Reference specific points from the meeting
- Provide requested information
- Suggest concrete next steps
- Include relevant resources or documentation
- Maintain momentum while being respectful of their timeline
        """,
        
        "./contexts/schools/status/interested.txt": """
For interested schools:
- Provide detailed implementation information
- Address any concerns raised
- Share success stories from similar institutions
- Discuss timeline and onboarding process
- Offer to connect with reference schools
        """,
        
        "./contexts/schools/status/enrolled.txt": """
For enrolled schools:
- Focus on successful implementation and support
- Share best practices and tips
- Provide ongoing training resources
- Check on satisfaction and identify growth opportunities
- Maintain relationship for renewals and referrals
        """,
        
        "./contexts/schools/info.txt": """
School-specific information:
- Educational discounts available
- FERPA compliance details
- Integration with common LMS platforms
- Student data privacy measures
- Academic calendar considerations
        """,
        
        "./contexts/companies/status/lead.txt": """
For new company leads:
- Professional introduction
- Focus on business value and ROI
- Request discovery call
- Keep initial outreach concise
- Highlight relevant industry experience
        """,
        
        "./contexts/companies/status/active.txt": """
For active company relationships:
- Regular check-ins on implementation
- Share new features and updates
- Identify expansion opportunities
- Maintain relationship with key stakeholders
- Proactive support and success management
        """,
        
        "./contexts/companies/status/closed.txt": """
For closed company deals:
- Ensure smooth implementation process
- Provide comprehensive onboarding
- Regular success check-ins
- Identify upselling opportunities
- Request testimonials and referrals
        """,
        
        "./contexts/companies/info.txt": """
Company-specific information:
- Enterprise features and pricing
- Security and compliance certifications
- Integration capabilities
- SLA and support options
- Scalability and customization options
        """,
        
        "./contexts/general_context.txt": """
General communication guidelines:
- Always be respectful and professional
- Response time expectation: within 24 hours
- Include clear call-to-action in each email
- Keep emails concise and scannable
- Use bullet points for multiple items
- Always offer to help with questions
        """,
        
        "./contexts/enhancer_context.txt": """
Email enhancement rules:
- Use active voice
- Remove filler words and redundancies
- Ensure mobile-friendly formatting
- Add signature block:

Best regards,
Alex Thompson
Senior Solutions Consultant
TechSolutions Inc.
alex.thompson@techsolutions.com | (555) 123-4567
www.techsolutions.com

- Check for:
  * Grammar and spelling
  * Consistent tone
  * Clear subject line
  * Proper formatting
  * All questions addressed
        """
    }
    
    # Create all context files
    for filepath, content in context_files.items():
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            f.write(content.strip())
    
    # Create initial metadata
    metadata = {
        "last_email_check": "2025-09-01 01:00:00",
        "last_context_refresh": "2025-09-01 10:00:00",
        "total_emails_processed": 0,
        "total_drafts_created": 0,
        "spreadsheet_id": "1zwaa4nqF2yPa1GqPTcAOrbjeMzvC42Jj7h_ta8G2O1c"
    }
    
    with open("./data/metadata.json", "w") as f:
        import json
        json.dump(metadata, f, indent=2)
    
    print("Directory structure created successfully!")
    print("\nCreated directories:")
    print("  ./data/")
    print("    ├── metadata.json")
    print("    ├── plans/")
    print("    └── traces/")
    print("  ./contexts/")
    print("    ├── schools/")
    print("    │   ├── status/")
    print("    │   │   ├── new.txt")
    print("    │   │   ├── meeting.txt")
    print("    │   │   ├── interested.txt")
    print("    │   │   └── enrolled.txt")
    print("    │   └── info.txt")
    print("    ├── companies/")
    print("    │   ├── status/")
    print("    │   │   ├── lead.txt")
    print("    │   │   ├── active.txt")
    print("    │   │   └── closed.txt")
    print("    │   └── info.txt")
    print("    ├── general_context.txt")
    print("    └── enhancer_context.txt")

if __name__ == "__main__":
    setup_directory_structure()