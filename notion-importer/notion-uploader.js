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
  
  // Initialize Notion client
  const notionClient = initNotionClient();
  
  // Map to store directory paths to their Notion page IDs
  const directoryPageMap = new Map();
  
  // Process the directory structure
  await processDirectory(notionClient, rootDir, null, directoryPageMap);
  
  console.log('Upload completed successfully!');
}

/**
 * Process a directory and its contents recursively
 * 
 * @param {Object} notionClient - The Notion client
 * @param {string} dirPath - Path to the directory
 * @param {string|null} parentPageId - ID of the parent page in Notion
 * @param {Map<string, string>} directoryPageMap - Map of directory paths to Notion page IDs
 * @returns {Promise<void>}
 */
async function processDirectory(notionClient, dirPath, parentPageId, directoryPageMap) {
  try {
    console.log(`Processing directory: ${dirPath}`);
    
    // Get the directory name
    const dirName = path.basename(dirPath);
    
    // Skip creating a page for the root directory if it's the input directory
    let currentPageId = parentPageId;
    if (dirPath !== config.inputDir) {
      // Create a page for this directory
      const dirPage = await createNotionPage(notionClient, {
        title: dirName,
        content: `Directory: ${dirName}`,
        parentPageId,
      });
      
      // Store the page ID in our map
      directoryPageMap.set(dirPath, dirPage.id);
      currentPageId = dirPage.id;
      
      console.log(`Created page for directory: ${dirName} (${dirPage.id})`);
    } else {
      // For the root directory, we'll use the database as the parent
      directoryPageMap.set(dirPath, null);
    }
    
    // Scan the directory for files and subdirectories
    const { directories, files } = await scanDirectory(dirPath);
    
    // Process all files in the directory
    for (const file of files) {
      await processFile(notionClient, file.path, currentPageId);
    }
    
    // Process all subdirectories
    for (const subdir of directories) {
      await processDirectory(notionClient, subdir.path, currentPageId, directoryPageMap);
    }
  } catch (error) {
    console.error(`Error processing directory ${dirPath}:`, error.message);
    throw error;
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
  let retries = 0;
  const maxRetries = config.api.maxRetries;
  
  while (retries <= maxRetries) {
    try {
      console.log(`Processing file: ${filePath}`);
      
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
      
      console.log(`✅ Created page for file: ${title} (${filePage.id})`);
      
      // Wait a bit to avoid rate limiting
      await new Promise(resolve => setTimeout(resolve, 1000 / config.api.requestsPerSecond));
      
      return filePage;
    } catch (error) {
      retries++;
      
      // Check if it's a rate limiting error or other Notion API error
      if (error.status === 429 || (error.code && error.code.includes('rate_limited'))) {
        const delay = Math.pow(2, retries) * config.api.retryDelay;
        console.warn(`⚠️ Rate limited! Retrying in ${delay / 1000} seconds... (Attempt ${retries} of ${maxRetries})`);
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }
      
      // If it's the last retry or not a rate limiting error
      if (retries > maxRetries) {
        console.error(`❌ Error processing file ${filePath} after ${maxRetries} retries:`, error.message);
        return null;
      }
      
      // For other errors, wait a bit before retrying
      const delay = config.api.retryDelay;
      console.warn(`⚠️ Error processing file! Retrying in ${delay / 1000} seconds... (Attempt ${retries} of ${maxRetries})`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  return null;
}

export default {
  uploadDirectoryToNotion,
};
