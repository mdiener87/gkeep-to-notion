import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

// Load environment variables
dotenv.config();

// Get the directory name of the current module
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Validate required environment variables
const requiredEnvVars = ['NOTION_API_KEY', 'NOTION_DATABASE_ID'];
const missingEnvVars = requiredEnvVars.filter(envVar => !process.env[envVar]);

if (missingEnvVars.length > 0) {
  console.error(`Error: Missing required environment variables: ${missingEnvVars.join(', ')}`);
  console.error('Please check your .env file or set these variables in your environment.');
  process.exit(1);
}

// Define and export configuration
const config = {
  // Notion API configuration
  notion: {
    apiKey: process.env.NOTION_API_KEY,
    databaseId: process.env.NOTION_DATABASE_ID,
  },
  
  // Input directory configuration
  inputDir: process.env.INPUT_DIR 
    ? path.resolve(process.env.INPUT_DIR) 
    : path.resolve(__dirname, '../output_markdown'),
  
  // Logging and debug options
  logging: {
    enabled: process.env.ENABLE_LOGGING === 'true',
    level: process.env.LOG_LEVEL || 'info',
  },
  
  // Rate limiting and API handling
  api: {
    maxRetries: parseInt(process.env.MAX_RETRIES || '3', 10),
    retryDelay: parseInt(process.env.RETRY_DELAY || '1000', 10),
    requestsPerSecond: parseInt(process.env.REQUESTS_PER_SECOND || '3', 10),
  },
  
  // Runtime options
  dryRun: process.env.DRY_RUN === 'true',
  verbose: process.env.VERBOSE === 'true'
};

export default config;
