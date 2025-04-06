# GKeep to Notion Importer

A Node.js application to import Google Keep markdown files into Notion while preserving directory structure and file order.

## Features

- Hierarchical import that maintains your directory structure
- Preserves numeric file sorting (e.g., `001_`, `002_`)
- Converts markdown to proper Notion blocks
- Extracts and preserves metadata (creation date, labels, etc.)
- Handles rate limiting and retries automatically
- Provides detailed progress reporting

## Prerequisites

- Node.js 16 or higher
- A Notion integration with API access
- A Notion database where pages will be created

## Setup

1. Clone this repository or navigate to the `notion-importer` directory

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create a `.env` file (based on `.env.example`) with the following:
   ```
   NOTION_API_KEY=your_notion_api_key_here
   NOTION_DATABASE_ID=your_notion_database_id_here
   INPUT_DIR=../output_markdown
   ```

   To get your Notion API key:
   - Go to https://www.notion.so/my-integrations
   - Create a new integration
   - Copy the "Internal Integration Token"

   To get your database ID:
   - Create a new database in Notion
   - Copy the ID from the URL: https://www.notion.so/workspace/[database-id]?v=...

## Usage

Run the importer with default settings:

```bash
npm start
```

Specify a custom input directory:

```bash
npm start -- --input /path/to/markdown/files
```

Additional options:

```bash
# Dry run (doesn't actually upload to Notion)
npm start -- --dry-run

# Verbose logging
npm start -- --verbose

# Show help
npm start -- --help
```

## Database Structure

Your Notion database should have the following properties for the best experience:

- `title` (Title property - required)
- `created` (Date property - optional, for file creation dates)
- `order` (Number property - optional, for preserving numeric order)
- `tags` (Multi-select property - optional, for labels)

## Limitations

- Notion API has rate limits (3 requests per second)
- Some markdown features may not translate perfectly to Notion blocks
- Large directories with many files may take time to process

## Troubleshooting

If you encounter errors:

1. Check your Notion API key and database ID
2. Verify that your integration has been added to the database
3. Ensure your markdown files are properly formatted
4. Try with the `--verbose` flag for more detailed logs

## License

MIT
