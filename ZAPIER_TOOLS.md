# Zapier MCP Tools Reference
*Auto-generated on 2025-08-21T20:00:13.467840*

## Summary
- Total tools available: 51
- Google Sheets tools: 28
- Gmail tools: 11
- LinkedIn tools: 3
- Firecrawl tools: 7
- Batch operations: 3

## Google Sheets Tools

### Batch Operations (Optimized for Multiple Items)
- **`zapier_google_sheets_lookup_spreadsheet_rows_advanced`** - Find up to 500 rows based on a column and value as line items.
- **`zapier_google_sheets_get_many_spreadsheet_rows_advanced`** - Return up to 1,500 rows as a single JSON value or as line items.
- **`zapier_google_sheets_create_multiple_spreadsheet_rows`** - Create one or more new rows in a specific spreadsheet (with line item support).

### Single Operations
- `zapier_google_sheets_find_worksheet` - Finds a worksheet by title.
- `zapier_google_sheets_get_data_range` - Get data from a specific range in a Google Spreadsheet using A1 notation (e.g., "A1:D10", "B2:E5").
- `zapier_google_sheets_get_row_by_id` - Get a specific spreadsheet row by its row number (ID). Row 1 is typically the header row.
- `zapier_google_sheets_get_spreadsheet_by_id` - Get a specific Google Spreadsheet by its ID. Returns the raw spreadsheet data from the Google Sheets API.
- `zapier_google_sheets_change_sheet_properties` - Update Google Sheets properties like frozen rows/columns, sheet position, and visibility settings.
- `zapier_google_sheets_lookup_spreadsheet_row` - Find a specific spreadsheet row based on a column and value. If found, it returns the entire row.
- `zapier_google_sheets_create_spreadsheet_column` - Create a new column in a specific spreadsheet.
- `zapier_google_sheets_create_spreadsheet_row` - Create a new row in a specific spreadsheet.
- `zapier_google_sheets_create_spreadsheet_row_at_top` - Creates a new spreadsheet row at the top of a spreadsheet (after the header row).
- `zapier_google_sheets_create_conditional_formatting_rule` - Apply conditional formatting to cells in a Google Sheets spreadsheet based on their values.
- `zapier_google_sheets_copy_range` - Copy data from one range to another within a Google Sheets spreadsheet, with options for what to paste (values, formatting, etc.).
- `zapier_google_sheets_copy_worksheet` - Creates a new worksheet by copying an existing worksheet.
- `zapier_google_sheets_create_spreadsheet` - Creates a new spreadsheet. Choose from a blank spreadsheet, a copy of an existing one, or one with headers.
- `zapier_google_sheets_create_worksheet` - Creates a new worksheet in a Google Sheet.
- `zapier_google_sheets_clear_spreadsheet_row_s` - Clears the contents of the selected row(s) while keeping the row(s) intact in the spreadsheet.
- `zapier_google_sheets_delete_sheet` - Permanently delete a worksheet from a Google Sheets spreadsheet. Warning: This action cannot be undone.
- `zapier_google_sheets_delete_spreadsheet_row_s` - Deletes the selected row(s) from the spreadsheet. This action removes the row(s) and all associated data.
- `zapier_google_sheets_format_cell_range` - Apply date, number, or style formatting (colors, bold, italic, strikethrough) to a range of cells in a Google Sheets spreadsheet.
- `zapier_google_sheets_format_spreadsheet_row` - Format a row in a specific spreadsheet.
- `zapier_google_sheets_rename_sheet` - Rename a worksheet in a Google Sheets spreadsheet.
- `zapier_google_sheets_set_data_validation` - Set data validation rules on a range of cells in Google Sheets to control what data can be entered.
- `zapier_google_sheets_sort_range` - Sort data within a specified range in Google Sheets by a chosen column in ascending or descending order.
- `zapier_google_sheets_update_spreadsheet_row` - Update a row in a specific spreadsheet with optional formatting.
- `zapier_google_sheets_update_spreadsheet_row_s` - Update one or more rows in a specific spreadsheet (with line item support).
- `zapier_google_sheets_api_request_beta` - This is an advanced action which makes a raw HTTP request that includes this integration's authentication.

## Gmail Tools
- `zapier_gmail_find_email` - Finds an email message.
- `zapier_gmail_add_label_to_email` - Add a label to an email message.
- `zapier_gmail_archive_email` - Archive an email message.
- `zapier_gmail_delete_email` - Sends an email message to the trash.
- `zapier_gmail_create_draft` - Create a draft email message.
*...and 6 more*

## LinkedIn Tools
- `zapier_linkedin_create_company_update` - Creates a new update for a Company Page.
- `zapier_linkedin_create_share_update` - Posts a status update sharing some content.
- `zapier_linkedin_api_request_beta` - This is an advanced action which makes a raw HTTP request that includes this integration's authentication.

## Firecrawl Tools
- `zapier_firecrawl_get_data_from_crawl` - Get the status and data from a crawl
- `zapier_firecrawl_get_data_from_extract` - Get the status and data from Extract 
- `zapier_firecrawl_scrape_structured_data_from_one_page_json_mode` - Scrapes a URL and returns extracted JSON data for a single page.
- `zapier_firecrawl_crawl_website` - Crawl a URL and return sub pages contents 
- `zapier_firecrawl_extract_structured_data_from_websites_with_ai` - Extract structured information
- `zapier_firecrawl_scrape_page` - Scrape a URL and return its contents
- `zapier_firecrawl_search_data` - Search and optionally scrape search results

## Optimization Recommendations

### For Web Scraper Workflow
1. **Batch Duplicate Checking**: Use `zapier_google_sheets_lookup_spreadsheet_rows_advanced` to check up to 500 rows at once
2. **Batch Creation**: Use `zapier_google_sheets_create_multiple_spreadsheet_rows` to add all new articles in one operation
3. **Batch Updates**: Use `zapier_google_sheets_update_spreadsheet_row_s` for multiple row updates
4. **Bulk Retrieval**: Use `zapier_google_sheets_get_many_spreadsheet_rows_advanced` to fetch up to 1,500 rows

### Token Saving Tips
- Combine multiple single operations into batch operations wherever possible
- Use `lookup_spreadsheet_rows_advanced` with smart filters instead of multiple single lookups
- Cache spreadsheet data locally when doing multiple operations on the same data
