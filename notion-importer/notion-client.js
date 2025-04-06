import { Client } from '@notionhq/client';
import config from './config.js';
import { processMarkdownContent } from './markdown-to-notion.js';

/**
 * Initialize and configure the Notion client
 * @returns {Client} Configured Notion API client
 */
export function initNotionClient() {
  const notion = new Client({
    auth: config.notion.apiKey,
  });
  
  return notion;
}

/**
 * Create a new page in Notion
 * 
 * @param {Client} notionClient - The Notion client
 * @param {Object} params - Page creation parameters
 * @param {string} params.title - Page title
 * @param {string} params.content - Page content in markdown
 * @param {string} [params.parentPageId] - Optional parent page ID for hierarchy
 * @param {Object} [params.properties] - Additional properties for the page
 * @returns {Promise<Object>} Created page object
 */
export async function createNotionPage(notionClient, { title, content, parentPageId, properties = {} }) {
  try {
    // Base properties with the title
    const pageProperties = {
      title: {
        title: [
          {
            text: {
              content: title,
            },
          },
        ],
      },
      // Add any additional properties
      ...properties,
    };

    // Create the page based on whether it has a parent or not
    const pageData = parentPageId 
      ? {
          parent: {
            page_id: parentPageId,
          },
          properties: pageProperties,
        }
      : {
          parent: {
            database_id: config.notion.databaseId,
          },
          properties: pageProperties,
        };

    // Create the page in Notion
    const createdPage = await notionClient.pages.create(pageData);

    // If there's content, append it to the page
    if (content) {
      await addContentToPage(notionClient, createdPage.id, content);
    }

    return createdPage;
  } catch (error) {
    console.error('Error creating Notion page:', error.message);
    throw error;
  }
}

/**
 * Add content blocks to an existing Notion page
 * 
 * @param {Client} notionClient - The Notion client
 * @param {string} pageId - ID of the page to update
 * @param {string} content - Content in markdown format
 * @returns {Promise<void>}
 */
async function addContentToPage(notionClient, pageId, content) {
  try {
    // Convert markdown to Notion blocks
    const blocks = processMarkdownContent(content);
    
    // Notion has a limit of 100 blocks per request, so we need to chunk our requests
    const chunkSize = 100;
    
    for (let i = 0; i < blocks.length; i += chunkSize) {
      const blockChunk = blocks.slice(i, i + chunkSize);
      
      await notionClient.blocks.children.append({
        block_id: pageId,
        children: blockChunk,
      });
      
      // Add a delay between chunked requests to avoid rate limiting
      if (i + chunkSize < blocks.length) {
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
  } catch (error) {
    console.error('Error adding content to Notion page:', error.message);
    throw error;
  }
}

export default {
  initNotionClient,
  createNotionPage,
};
