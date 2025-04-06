import path from 'path';
import { initNotionClient, createNotionPage } from './notion-client.js';
import { scanDirectory, readMarkdownFile } from './file-processor.js';
import config from './config.js';

/**
 * Main function to upload a directory structure to Notion
 * 
 * @param {string} rootDir - The root directory to upload
 * @returns {Promise<void>}
 */
export async function uploadDirectoryToNotion(rootDir) {
  console.log(`Starting upload of directory: ${rootDir}`);
  
  if (config.dryRun) {
    console.log('🔍 DRY RUN MODE: No actual uploads will be performed');
  }
  
  // Initialize Notion client
  const notionClient = initNotionClient();
  
  // Map to store directory paths to their Notion page IDs
  const directoryPageMap = new Map();
  
  // Stats for tracking progress
  const stats = {
    directoriesProcessed: 0,
    filesProcessed: 0,
    failures: 0,
  };
  
  // Process the directory structure
  await processDirectory(notionClient, rootDir, null, directoryPageMap, stats);
  
  // Log statistics
  console.log('\n📊 Upload Statistics:');
  console.log(`   - Directories processed: ${stats.directoriesProcessed}`);
  console.log(`   - Files processed: ${stats.filesProcessed}`);
  console.log(`   - Failed uploads: ${stats.failures}`);
  
  console.log('\nUpload completed successfully!');
}

/**
 * Process a directory and its contents recursively
 * 
 * @param {Object} notionClient - The Notion client
 * @param {string} dirPath - Path to the directory
 * @param {string|null} parentPageId - ID of the parent page in Notion
 * @param {Map<string, string>} directoryPageMap - Map of directory paths to Notion page IDs
 * @param {Object} stats - Statistics object for tracking progress
 * @returns {Promise<void>}
 */
async function processDirectory(notionClient, dirPath, parentPageId, directoryPageMap, stats) {
  try {
    if (config.verbose) {
      console.log(`\n📁 Processing directory: ${dirPath}`);
    } else {
      process.stdout.write(`\rProcessing: ${path.basename(dirPath)}...`);
    }
    
    // Get the directory name
    const dirName = path.basename(dirPath);
    
    // Skip creating a page for the root directory if it's the input directory
    let currentPageId = parentPageId;
    let dirPageId = null;
    
    if (dirPath !== config.inputDir) {
      if (!config.dryRun) {
        // Create a page for this directory
        const dirPage = await createNotionPage(notionClient, {
          title: dirName,
          content: `Directory: ${dirName}`,
          parentPageId,
        });
        
        // Store the page ID in our map
        directoryPageMap.set(dirPath, dirPage.id);
        currentPageId = dirPage.id;
        dirPageId = dirPage.id;
        
        if (config.verbose) {
          console.log(`   ✅ Created page for directory: ${dirName} (${dirPage.id})`);
        }
      } else {
        // In dry-run mode, create a fake ID
        const fakeId = `dry-run-dir-${Math.random().toString(36).substring(2, 10)}`;
        directoryPageMap.set(dirPath, fakeId);
        currentPageId = fakeId;
        dirPageId = fakeId;
        
        if (config.verbose) {
          console.log(`   🔍 [DRY RUN] Would create page for directory: ${dirName}`);
        }
      }
      
      // Increment directory counter
      stats.directoriesProcessed++;
    } else {
      // For the root directory, we'll use the database as the parent
      directoryPageMap.set(dirPath, null);
      
      if (config.verbose) {
        console.log(`   ℹ️ Using root database for directory: ${dirName}`);
      }
    }
    
    // Scan the directory for files and subdirectories
    const { directories, files } = await scanDirectory(dirPath);
    
    if (config.verbose) {
      console.log(`   📊 Found ${files.length} files and ${directories.length} subdirectories`);
    }
    
    // Process all files in the directory
    for (const file of files) {
      const fileResult = await processFile(notionClient, file.path, currentPageId);
      if (!fileResult && !config.dryRun) {
        stats.failures++;
      }
      stats.filesProcessed++;
    }
    
    // Process all subdirectories
    for (const subdir of directories) {
      await processDirectory(notionClient, subdir.path, currentPageId, directoryPageMap, stats);
    }
    
    if (config.verbose && dirPath !== config.inputDir) {
      console.log(`   ✅ Completed directory: ${dirName}${dirPageId ? ` (${dirPageId})` : ''}`);
    }
  } catch (error) {
    console.error(`\n❌ Error processing directory ${dirPath}:`, error.message);
    stats.failures++;
    
    // Continue with other directories rather than stopping the whole process
    console.error('   ⚠️ Continuing with next directory...');
  }
}

/**
 * Process a markdown file and upload it to Notion
 * 
 * @param {Object} notionClient - The Notion client
 * @param {string} filePath - Path to the markdown file
 * @param {string|null} parentPageId - ID of the parent page in Notion
 * @returns {Promise<Object|null>} Created page or null if failed
 */
async function processFile(notionClient, filePath, parentPageId) {
  const fileName = path.basename(filePath);
  
  if (config.verbose) {
    console.log(`   📄 Processing file: ${fileName}`);
  } else {
    process.stdout.write(`\rProcessing: ${fileName}...`);
  }
  
  // If in dry-run mode, just log what would happen
  if (config.dryRun) {
    try {
      // Read and parse the markdown file to show what would be processed
      const { title, content, metaData } = await readMarkdownFile(filePath);
      
      if (config.verbose) {
        console.log(`      🔍 [DRY RUN] Would create page for: ${title}`);
        console.log(`      🔍 Metadata: ${JSON.stringify(metaData)}`);
        console.log(`      🔍 Content length: ${content.length} characters`);
      }
      
      // Simulate processing delay
      await new Promise(resolve => setTimeout(resolve, 100));
      
      return { id: `dry-run-file-${Math.random().toString(36).substring(2, 10)}` };
    } catch (error) {
      console.error(`      ❌ [DRY RUN] Error reading file ${filePath}:`, error.message);
      return null;
    }
  }
  
  // Actual file processing logic (when not in dry-run mode)
  let retries = 0;
  const maxRetries = config.api.maxRetries;
  
  while (retries <= maxRetries) {
    try {
      // Read and parse the markdown file
      const { title, content, metaData } = await readMarkdownFile(filePath);
      
      // Prepare additional properties for the page
      const additionalProperties = {};
      
      // Add metadata as properties if available
      if (metaData.created) {
        additionalProperties.created = {
          type: 'date',
          date: {
            start: new Date(metaData.created).toISOString(),
          },
        };
      }
      
      if (metaData.order !== undefined) {
        additionalProperties.order = {
          type: 'number',
          number: metaData.order,
        };
      }
      
      if (metaData.labels && metaData.labels.length > 0) {
        additionalProperties.tags = {
          type: 'multi_select',
          multi_select: metaData.labels.map(label => ({ name: label })),
        };
      }
      
      // Create a page for this file
      const filePage = await createNotionPage(notionClient, {
        title,
        content,
        parentPageId,
        properties: additionalProperties,
      });
      
      if (config.verbose) {
        console.log(`      ✅ Created page for file: ${title} (${filePage.id})`);
      }
      
      // Wait a bit to avoid rate limiting
      await new Promise(resolve => setTimeout(resolve, 1000 / config.api.requestsPerSecond));
      
      return filePage;
    } catch (error) {
      retries++;
      
      // Check if it's a rate limiting error or other Notion API error
      if (error.status === 429 || (error.code && error.code.includes('rate_limited'))) {
        const delay = Math.pow(2, retries) * config.api.retryDelay;
        console.warn(`      ⚠️ Rate limited! Retrying in ${delay / 1000} seconds... (Attempt ${retries} of ${maxRetries})`);
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }
      
      // If it's the last retry or not a rate limiting error
      if (retries > maxRetries) {
        console.error(`      ❌ Error processing file ${filePath} after ${maxRetries} retries:`, error.message);
        return null;
      }
      
      // For other errors, wait a bit before retrying
      const delay = config.api.retryDelay;
      console.warn(`      ⚠️ Error processing file! Retrying in ${delay / 1000} seconds... (Attempt ${retries} of ${maxRetries})`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  return null;
}

export default {
  uploadDirectoryToNotion,
};
