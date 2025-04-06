#!/usr/bin/env node

import path from 'path';
import minimist from 'minimist';
import { uploadDirectoryToNotion } from './notion-uploader.js';
import config from './config.js';

// Parse command line arguments
const argv = minimist(process.argv.slice(2), {
  string: ['input'],
  boolean: ['dry-run', 'verbose'],
  alias: {
    i: 'input',
    h: 'help',
    d: 'dry-run',
    v: 'verbose',
  },
});

// Show help if requested
if (argv.help) {
  console.log(`
  Notion Importer - Upload markdown files to Notion

  Usage:
    npm start -- [options]

  Options:
    -i, --input     Specify input directory (defaults to ../output_markdown)
    -d, --dry-run   Simulate upload without actually sending to Notion
    -v, --verbose   Show detailed progress and debug information
    -h, --help      Show this help message

  Environment Variables (can be set in .env file):
    NOTION_API_KEY      Your Notion API key (required)
    NOTION_DATABASE_ID  Notion database ID for the root pages (required)
    INPUT_DIR           Input directory path (alternative to --input flag)
    ENABLE_LOGGING      Enable detailed logging (true/false)
    MAX_RETRIES         Maximum number of retries for API calls (default: 3)
    RETRY_DELAY         Base delay between retries in ms (default: 1000)
    REQUESTS_PER_SECOND Rate limit for API requests (default: 3)
  `);
  process.exit(0);
}

// Display a fancy banner
function displayBanner() {
  console.log('');
  console.log('🌟 '.repeat(12));
  console.log('');
  console.log('   𝐆𝐊𝐄𝐄𝐏 𝐓𝐎 𝐍𝐎𝐓𝐈𝐎𝐍 𝐈𝐌𝐏𝐎𝐑𝐓𝐄𝐑   ');
  console.log('');
  console.log('🌟 '.repeat(12));
  console.log('');
}

// Main function
async function main() {
  try {
    // Determine input directory
    const inputDir = argv.input || config.inputDir;
    const dryRun = argv['dry-run'] || false;
    const verbose = argv.verbose || config.logging.enabled;
    
    // Update config with command line options
    config.logging.enabled = verbose;
    config.dryRun = dryRun;
    
    // Display banner and configuration
    displayBanner();
    console.log('📋 Configuration:');
    console.log(`   - Input Directory: ${inputDir}`);
    console.log(`   - Notion Database ID: ${config.notion.databaseId.substring(0, 8)}...`);
    console.log(`   - Dry Run: ${dryRun ? 'Yes (no actual uploads)' : 'No (will upload to Notion)'}`);
    console.log(`   - Verbose Logging: ${verbose ? 'Enabled' : 'Disabled'}`);
    console.log(`   - Requests Per Second: ${config.api.requestsPerSecond}`);
    console.log(`   - Max Retries: ${config.api.maxRetries}`);
    console.log('');
    
    // Confirm with user
    console.log('⚡ Starting import process...');
    console.log('');
    
    // Start the upload process
    const startTime = Date.now();
    await uploadDirectoryToNotion(inputDir);
    const endTime = Date.now();
    const duration = (endTime - startTime) / 1000; // in seconds
    
    console.log('');
    console.log('✅ Import completed successfully!');
    console.log(`   - Total time: ${duration.toFixed(2)} seconds`);
    console.log('');
    console.log('📝 Next steps:');
    console.log('   - Check your Notion database to verify the imported content');
    console.log('   - You may need to adjust the database view to see all imported pages');
    console.log('');
  } catch (error) {
    console.error('❌ Error during import process:');
    console.error(error);
    process.exit(1);
  }
}

// Execute main function
main();
