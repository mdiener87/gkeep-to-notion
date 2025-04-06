import fs from 'fs-extra';
import path from 'path';
import { glob } from 'glob';

/**
 * Recursively scan a directory and return all files and directories
 * 
 * @param {string} rootDir - The root directory to scan
 * @returns {Promise<Object>} - Object with sorted directories and files
 */
export async function scanDirectory(rootDir) {
  try {
    // Make sure the directory exists
    if (!await fs.pathExists(rootDir)) {
      throw new Error(`Directory does not exist: ${rootDir}`);
    }
    
    // Read directory contents
    const entries = await fs.readdir(rootDir, { withFileTypes: true });
    
    // Separate files and directories
    const files = [];
    const directories = [];
    
    for (const entry of entries) {
      const fullPath = path.join(rootDir, entry.name);
      
      if (entry.isDirectory()) {
        directories.push({
          name: entry.name,
          path: fullPath,
        });
      } else if (entry.isFile() && path.extname(entry.name).toLowerCase() === '.md') {
        // Only include markdown files
        files.push({
          name: entry.name,
          path: fullPath,
        });
      }
    }
    
    // Sort directories alphabetically
    directories.sort((a, b) => a.name.localeCompare(b.name));
    
    // Sort files numerically by prefix if possible, then alphabetically
    files.sort((a, b) => {
      // Try to extract numeric prefixes (like "001_" from "001_Session 01")
      const prefixA = a.name.match(/^(\d+)_/);
      const prefixB = b.name.match(/^(\d+)_/);
      
      if (prefixA && prefixB) {
        // Compare numerically if both have numeric prefixes
        return parseInt(prefixA[1], 10) - parseInt(prefixB[1], 10);
      }
      
      // Fall back to alphabetical comparison
      return a.name.localeCompare(b.name);
    });
    
    return { directories, files };
  } catch (error) {
    console.error(`Error scanning directory ${rootDir}:`, error.message);
    throw error;
  }
}

/**
 * Read and parse a markdown file
 * 
 * @param {string} filePath - Path to the markdown file
 * @returns {Promise<Object>} Parsed file data
 */
export async function readMarkdownFile(filePath) {
  try {
    // Read the file
    const content = await fs.readFile(filePath, 'utf8');
    
    // Extract the title from the file name or first heading
    let title = path.basename(filePath, '.md');
    
    // Remove numeric prefix if it exists (e.g., "001_" from "001_Session 01")
    title = title.replace(/^\d+_/, '');
    
    // Try to extract title from first heading in the content
    const headingMatch = content.match(/^# (.+)$/m);
    if (headingMatch) {
      title = headingMatch[1].trim();
    }
    
    // Parse metadata
    const metaData = {};
    const metaMatch = content.match(/\*\*Created:\*\* (.*?)  \n\s+\*\*Last Edited:\*\* (.*?)  \n\s+\*\*Labels:\*\* (.*?)  /);
    
    if (metaMatch) {
      metaData.created = metaMatch[1];
      metaData.lastEdited = metaMatch[2];
      metaData.labels = metaMatch[3].split(',').map(label => label.trim());
    }
    
    // Extract original file name and order
    const fileNameData = path.basename(filePath, '.md');
    const orderMatch = fileNameData.match(/^(\d+)_/);
    
    if (orderMatch) {
      metaData.order = parseInt(orderMatch[1], 10);
      metaData.originalFileName = fileNameData;
    }
    
    return {
      title,
      content,
      metaData,
      filePath,
    };
  } catch (error) {
    console.error(`Error reading markdown file ${filePath}:`, error.message);
    throw error;
  }
}

/**
 * Find all markdown files recursively in a directory
 * 
 * @param {string} rootDir - The root directory to scan
 * @returns {Promise<Array<string>>} - Array of file paths
 */
export async function findAllMarkdownFiles(rootDir) {
  try {
    const files = await glob('**/*.md', { 
      cwd: rootDir,
      absolute: true
    });
    
    return files;
  } catch (error) {
    console.error(`Error finding markdown files in ${rootDir}:`, error.message);
    throw error;
  }
}

export default {
  scanDirectory,
  readMarkdownFile,
  findAllMarkdownFiles,
};
