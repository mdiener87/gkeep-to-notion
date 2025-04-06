#!/usr/bin/env node

import fs from 'fs-extra';
import path from 'path';
import { fileURLToPath } from 'url';
import readline from 'readline';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

// Get the directory name of the current module
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Create readline interface
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

// Helper to ask questions
function question(query) {
  return new Promise((resolve) => {
    rl.question(query, resolve);
  });
}

// Main setup function
async function setup() {
  console.log('\n🚀 Welcome to the GKeep to Notion Importer Setup!\n');
  
  try {
    // Check if .env file already exists
    const envPath = path.join(__dirname, '.env');
    const envExists = await fs.pathExists(envPath);
    
    if (envExists) {
      const overwrite = await question('An .env file already exists. Overwrite it? (y/n): ');
      if (overwrite.toLowerCase() !== 'y') {
        console.log('\n✅ Setup canceled. Your existing .env file remains unchanged.\n');
        rl.close();
        return;
      }
    }
    
    // Ask for Notion API key
    const apiKey = await question('Enter your Notion API key: ');
    if (!apiKey) {
      throw new Error('Notion API key is required');
    }
    
    // Ask for Notion database ID
    const databaseId = await question('Enter your Notion database ID: ');
    if (!databaseId) {
      throw new Error('Notion database ID is required');
    }
    
    // Ask for input directory path (with default)
    const defaultInputDir = path.resolve(__dirname, '../output_markdown');
    const inputDir = await question(`Enter the input directory path (default: ${defaultInputDir}): `) || defaultInputDir;
    
    // Create .env file
    const envContent = `# Notion API Key
NOTION_API_KEY=${apiKey}

# Notion Database ID where pages will be created
NOTION_DATABASE_ID=${databaseId}

# Input directory path (relative to the project root or absolute)
INPUT_DIR=${inputDir}

# API handling options
MAX_RETRIES=3
RETRY_DELAY=1000
REQUESTS_PER_SECOND=3

# Logging options
ENABLE_LOGGING=false
`;
    
    await fs.writeFile(envPath, envContent);
    console.log('\n✅ .env file created successfully!\n');
    
    // Install dependencies if needed
    const packageLockExists = await fs.pathExists(path.join(__dirname, 'package-lock.json'));
    const nodeModulesExists = await fs.pathExists(path.join(__dirname, 'node_modules'));
    
    if (!packageLockExists || !nodeModulesExists) {
      console.log('📦 Installing dependencies...');
      try {
        await execAsync('npm install', { cwd: __dirname });
        console.log('✅ Dependencies installed successfully!');
      } catch (error) {
        console.error('⚠️ Error installing dependencies:', error.message);
        console.log('Please run "npm install" manually in the notion-importer directory.');
      }
    }
    
    console.log('\n🎉 Setup completed! You can now run the importer with:');
    console.log('   npm start\n');
    console.log('For more options, run:');
    console.log('   npm start -- --help\n');
    
  } catch (error) {
    console.error('\n❌ Setup failed:', error.message);
    console.log('Please check the error and try again.\n');
  } finally {
    rl.close();
  }
}

// Run setup
setup();
