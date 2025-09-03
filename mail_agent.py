import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.orchestrator.orchestrator import Orchestrator
from mcp_agent.workflows.llm.augmented_llm_anthropic import AnthropicAugmentedLLM
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EmailManagementSystem:
    def __init__(self):
        """
        Initialize the email management system
        
        Directory structure expected:
        ./data/
            metadata.json
            plans/
            traces/
        ./contexts/
            schools/
                status/
                    new.txt
                    meeting.txt
                    interested.txt
                    enrolled.txt
                info.txt
            companies/
                status/
                    lead.txt
                    active.txt
                    closed.txt
                info.txt
            general_context.txt
            enhancer_context.txt
        """
        self.data_dir = Path('./data')
        self.context_dir = Path('./contexts')
        self.plans_dir = self.data_dir / "plans"
        self.traces_dir = self.data_dir / "traces"
        self.metadata_file = self.data_dir / "metadata.json"
        
        # Create directories
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or initialize metadata
        self.metadata = self.load_metadata()
        
        # Initialize MCP app
        self.app = MCPApp(name="email_management")
        
    def load_metadata(self) -> Dict:
        """Load or create metadata file"""
        if self.metadata_file.exists():
            with open(self.metadata_file) as f:
                return json.load(f)
        else:
            # Get spreadsheet ID from environment
            spreadsheet_id = os.getenv("EMAIL_CRM_SPREADSHEET_ID")
            if not spreadsheet_id:
                raise ValueError("EMAIL_CRM_SPREADSHEET_ID environment variable is required")
                
            initial_metadata = {
                "last_email_check": "2025-09-01 01:00:00",
                "last_context_refresh": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_emails_processed": 0,
                "total_drafts_created": 0,
                "spreadsheet_id": spreadsheet_id
            }
            self.save_metadata(initial_metadata)
            return initial_metadata
    
    def save_metadata(self, metadata: Dict):
        """Save metadata to file"""
        with open(self.metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
        self.metadata = metadata
    
    def create_agents(self):
        """Create all specialized agents with specific instructions"""
        
        # 1. State Manager Agent - Manages metadata and state
        self.state_manager = Agent(
            name="file_manager",
            instruction=f"""You are the state management agent. Your responsibilities:
            
            1. Read and update metadata from {self.metadata_file}
            2. Track last_email_check timestamp in format YYYY-MM-DD HH:MM:SS
            3. Maintain contact status cache in spreadsheet
            4. Update processing statistics
            
            Current metadata location: {self.metadata_file}
            
            When asked to get state:
            - Read the JSON file using filesystem tools
            - Return the current last_email_check and other metadata
            
            When asked to update state:
            - Update the timestamp to current time
            - Increment counters as needed
            - Save back to the JSON file
            """,
            server_names=["filesystem", "zapier"]
            # Note: 'zapier' server provides Gmail, Google Sheets, and other productivity tools
            # 'filesystem' server provides file read/write operations for metadata.json
        )
        
        # 2. Email Monitor Agent - Checks and logs new emails
        self.email_monitor = Agent(
            name="gmail_manager",
            instruction=f"""You are the email monitoring agent with access to Gmail and Google Sheets via zapier server.
            
            Available tools: gmail_find_email, gmail_get_thread, sheets_lookup_row, sheets_create_row, sheets_update_row
            
            1. Check Gmail for new emails using gmail_find_email tool
            2. Use query: "in:inbox after:{{last_check_date}}"
               - Format date as: after:YYYY/MM/DD or use relative like after:1d
            3. For EACH new email found:
               a. Extract: sender email, subject, message_id, thread_id, received date
               b. Check if email exists in spreadsheet (lookup by message_id)
               c. If new, create row with these columns:
                  - email: sender's email address
                  - subject: email subject line
                  - message_id: unique Gmail ID
                  - thread_id: conversation thread ID
                  - received_date: when received
                  - type: (leave empty for classification)
                  - status: "new"
                  - action_required: 1 if needs response, 0 if FYI/newsletter
                  - notes: (empty initially)
                  - last_processed: current timestamp
               d. For managing is_latest flag:
                  - Set is_latest = 1 for this new row
                  - Find ALL previous rows with same sender email address
                  - Update those rows: set is_latest = 0
                  - This ensures only the newest email per contact has is_latest = 1
            
            4. Return list of new emails found with their details
            5. Mark action_required=1 for emails that need responses
            
            IMPORTANT: Only process emails that are NOT already in the spreadsheet.
            Use sheets_lookup_row to check if message_id exists before adding.
            """,
            server_names=["zapier"]
            # tool_filter=lambda t: t.name in [
            #    "gmail_find_email",
            #   "gmail_get_thread",
            #   "sheets_create_row",
            #   "sheets_lookup_row"
            # ]
        )
        
        # 3. Contact Classifier - Determines contact type
        self.contact_classifier = Agent(
            name="email_classifier",
            instruction=f"""You are the contact classification agent with access to Gmail and Google Sheets via zapier server.
            
            Available tools: gmail_get_thread, sheets_lookup_row, sheets_update_row
            
            1. For each email with empty 'type' field in spreadsheet:
               a. Get full email content using gmail_get_thread with thread_id
               b. Analyze BOTH sender's domain AND email content
               c. Classify as one of: "school", "company", "personal", "other"
               
            2. Classification strategy (use BOTH domain AND content):
               a. Domain indicators:
                  - .edu domains → likely "school"
                  - Corporate domains → likely "company"
                  - Gmail/Yahoo/personal → likely "personal"
               
               b. Content indicators (override domain when clear):
                  - Educational keywords (course, program, student, university, degree) → "school"
                  - Business keywords (partnership, services, proposal, meeting, sales) → "company"
                  - Personal keywords (thanks, personal inquiry, casual tone) → "personal"
                  - Newsletters, automated messages → "other"
               
               c. Final decision:
                  - If content clearly indicates type, use content classification
                  - If content is ambiguous, use domain classification
                  - If both unclear, classify as "other"
            
            3. Update the row in spreadsheet with:
               - type: classified type
               - status: initial status based on type
                 * school → "new"
                 * company → "lead"
                 * personal → "active"
                 * other → "pending"
            
            4. Use sheets_lookup_row to find unclassified emails
            5. Use gmail_get_thread to get email content for analysis
            6. Use sheets_update_row to update type and status
            """,
            server_names=["zapier"],
        )
        
        # 4. Context Aggregator - Gathers all relevant context
        self.context_aggregator = Agent(
            name="context_gatherer",
            instruction=f"""You are the context aggregation agent with access to Gmail via zapier server and filesystem.
            
            Available tools: gmail_get_thread, sheets_lookup_row (via zapier) and file read/write (via filesystem)
            
            1. For each email marked with action_required=1:
               a. Read from spreadsheet: email, type, status, thread_id, notes
               b. Fetch full conversation history using gmail_get_thread with thread_id
               c. Load context files based on type and status:
                  - Read {self.context_dir}/{{type}}/status/{{status}}.txt
                  - Read {self.context_dir}/{{type}}/info.txt
                  - Read {self.context_dir}/general_context.txt
               
            2. Create a context package containing:
               - Contact email and type
               - Current status
               - Full conversation history
               - Relevant context files content
               - Any existing notes from spreadsheet
               - Important facts from previous exchanges
            
            3. Return structured context for each email needing response
            
            File paths to use:
            - Schools: {self.context_dir}/schools/status/[new|meeting|interested|enrolled].txt
            - Companies: {self.context_dir}/companies/status/[lead|active|closed].txt
            - Info files: {self.context_dir}/[schools|companies]/info.txt
            - General: {self.context_dir}/general_context.txt
            """,
            server_names=["zapier", "filesystem"]
        )
        
        # 5. Draft Generator - Creates email drafts
        self.draft_generator = Agent(
            name="draft_generator",
            instruction=f"""You are the email draft generation agent. Your responsibilities:
            
            1. For each context package provided:
               a. Analyze the conversation history to understand context
               b. Use the status-specific guidelines from context files
               c. Apply the general context rules
               d. Generate an appropriate email response
            
            2. Draft guidelines based on type and status:
               - school/new: Introduction, value proposition, meeting request
               - school/meeting: Follow up on meeting, provide requested info
               - school/interested: Detailed information, next steps
               - company/lead: Initial outreach, establish connection
               - company/active: Ongoing support, relationship building
            
            3. Email structure:
               - Appropriate greeting
               - Reference to previous conversation if applicable
               - Main content addressing their questions/needs
               - Clear next steps or call-to-action
               - Professional closing
               - [Signature will be added by enhancer]
            
            4. Suggest status updates:
               - If school/new had positive response → "meeting"
               - If school/meeting showed interest → "interested"
               - If company/lead responded → "active"
            
            5. Output format:
               - draft_text: The email draft
               - suggested_status: New status if applicable
               - follow_up_date: Suggested follow-up date
               - priority: high/medium/low
            
            Remember: Do NOT send or save drafts, only generate text.
            """,
            server_names=[]  # No tools needed, pure generation
        )
        
        # 6. Draft Enhancer - Polishes drafts
        self.draft_enhancer = Agent(
            name="draft_enhancer",
            instruction=f"""You are the email enhancement agent. Your responsibilities:
            
            1. Read enhancer context from {self.context_dir}/enhancer_context.txt
            2. For each draft provided:
               a. Apply grammar and style improvements
               b. Ensure consistent brand voice from enhancer_context.txt
               c. Check tone is appropriate for recipient type
               d. Add proper signature from context
               e. Ensure all questions are addressed
            
            3. Enhancement checklist:
               - Grammar and spelling correct
               - Tone matches recipient type (formal for schools, friendly for personal)
               - No redundant phrases
               - Clear and concise language
               - Proper formatting (paragraphs, spacing)
               - Signature block added
            
            4. Return enhanced draft ready for sending
            
            Context file: {self.context_dir}/enhancer_context.txt
            """,
            server_names=["filesystem"]
        )
        
        # 7. Action Executor - Performs all write operations
        self.action_executor = Agent(
            name="spreadsheet_manager",
            instruction=f"""You are the action execution agent with access to Gmail and Google Sheets via zapier server.
            
            Available tools: gmail_create_draft, sheets_update_row, sheets_lookup_row (via zapier)
            
            1. Save email drafts to Gmail:
               - Use gmail_create_draft with enhanced draft text
               - Include proper subject line (Re: original subject)
               - Set reply_to thread_id for conversation continuity
            
            2. Update spreadsheet for each processed email:
               - Set action_required = 0 (draft created)
               - Update status if suggested
               - Add note with summary of response
               - Update last_processed timestamp
               - Set follow_up_date if provided
            
            3. Create activity log in notes column:
               - Date: Draft created for [topic]
               - Status changed from X to Y
               - Follow-up scheduled for [date]
            
            4. Ensure atomic operations:
               - All updates must succeed or rollback
               - If draft creation fails, don't update spreadsheet
               - Log any errors to notes field
            
            5. Return summary of actions taken:
               - Number of drafts created
               - Status updates made
               - Any errors encountered
            
            Use these tools in order:
            1. gmail_create_draft for each email
            2. sheets_update_row to update spreadsheet
            """,
            server_names=["zapier"],
        )
    
    async def process_new_emails(self, use_cached_plan: bool = True, custom_task: str = None):
            """Main workflow: Check new emails and create drafts"""
            
            async with self.app.run() as context:
                # Create agents
                self.create_agents()
                
                # Create orchestrator with plan output
                orchestrator = Orchestrator(
                    worker_agents=[
                        self.state_manager,
                        self.email_monitor,
                        self.contact_classifier,
                        self.context_aggregator,
                        self.draft_generator,
                        self.draft_enhancer,
                        self.action_executor
                    ],
                    llm_factory=AnthropicAugmentedLLM,
                    plan_type="full",
                    plan_output_path=self.plans_dir / f"email_workflow_{datetime.now():%Y%m%d_%H%M%S}.md"
                )
            
            # Use custom task if provided, otherwise load from file
            if custom_task:
                task = custom_task
            else:
                task_file = self.context_dir / "cron_draft_task.txt"
                if task_file.exists():
                    with open(task_file) as f:
                        task = f.read()
                else:
                    task = "No task file found and no custom task provided"
            
            # Execute with tracking
            trace_file = self.traces_dir / f"{datetime.now():%Y%m%d_%H%M%S}_trace.json"
            
            # Execute orchestrator
            result = await orchestrator.generate_str(task)
            
            # Update metadata
            self.metadata["last_email_check"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.metadata["total_emails_processed"] += 1  # Update based on actual result
            self.save_metadata(self.metadata)
            
            # Save execution trace
            with open(trace_file, "w") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "task": task,
                    "result": result,
                    "metadata": self.metadata
                }, f, indent=2)
            
            return result
    
    async def create_single_email(self, recipient_email: str, message: str):
        """Create a single email with context"""
        
        async with self.app.run() as context:
            self.create_agents()
            
            orchestrator = Orchestrator(
                worker_agents=[
                    self.contact_classifier,
                    self.context_aggregator,
                    self.draft_generator,
                    self.draft_enhancer,
                    self.action_executor
                ],
                llm_factory=AnthropicAugmentedLLM,
                plan_type="iterative"
            )
            
            task = f"""
            Create an email to {recipient_email}:
            
            1. LOOKUP:
               - Check if contact exists in spreadsheet
               - Get their type and status if exists
               - Get conversation history from Gmail
            
            2. CONTEXT:
               - Load relevant context based on type
               - Include conversation history
               - Apply appropriate tone and approach
            
            3. DRAFT:
               - Create email with message: "{message}"
               - Incorporate context appropriately
               - Maintain conversation continuity
            
            4. ENHANCE:
               - Polish the draft
               - Add signature
            
            5. SAVE:
               - Create draft in Gmail
               - Update/create spreadsheet entry
               - Set follow-up reminder if needed
            
            Return the created draft text.
            """
            
            result = await orchestrator.generate_str(task)
            return result

# Test function
async def test_state_manager():
    """Test if state_manager agent can read metadata file"""
    system = EmailManagementSystem()
    
    async with system.app.run() as context:
        system.create_agents()
        
        # Test state_manager directly
        from mcp_agent.workflows.llm.augmented_llm_anthropic import AnthropicAugmentedLLM
        
        async with system.state_manager:
            llm = await system.state_manager.attach_llm(AnthropicAugmentedLLM)
            
            print("Testing state_manager agent file reading...")
            result = await llm.generate_str(f"Read the metadata file at {system.metadata_file} and return its contents")
            
            print("State manager test result:")
            print(result)

# Main execution
async def main():
    # Test state manager first
    print("Testing state_manager agent...")
    await test_state_manager()
    
    print("\n" + "="*50)
    print("Now testing full workflow...")
    
    # Initialize system
    system = EmailManagementSystem()
    
    # Process new emails
    print("Processing new emails...")
    result = await system.process_new_emails(use_cached_plan=True)
    print(f"Result: {result}")
    
    # Or create a single email
    # result = await system.create_single_email(
    #     "john@school.edu",
    #     "Following up on our discussion about the new program"
    # )

if __name__ == "__main__":
    asyncio.run(main())
