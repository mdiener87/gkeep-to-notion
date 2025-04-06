import MarkdownIt from 'markdown-it';

// Initialize the Markdown parser
const md = new MarkdownIt();

/**
 * Convert Markdown content to Notion API blocks
 * 
 * @param {string} markdownContent - Raw markdown content
 * @returns {Array} Array of Notion blocks ready for the API
 */
export function convertMarkdownToNotionBlocks(markdownContent) {
  const notionBlocks = [];
  
  // Split content into lines for easier processing
  const lines = markdownContent.split('\n');
  
  // Process lines one by one
  let i = 0;
  while (i < lines.length) {
    const line = lines[i].trim();
    
    // Skip empty lines
    if (!line) {
      i++;
      continue;
    }
    
    // Process headings
    if (line.startsWith('#')) {
      const headingLevel = line.match(/^(#+)/)[0].length;
      const headingText = line.substring(headingLevel).trim();
      
      notionBlocks.push(createHeadingBlock(headingText, headingLevel));
      i++;
      continue;
    }
    
    // Process lists
    if (line.match(/^[\*\-] /)) {
      // Collect all list items
      const listItems = [];
      let j = i;
      
      while (j < lines.length && lines[j].trim().match(/^[\*\-] /)) {
        listItems.push(lines[j].trim().substring(2));
        j++;
      }
      
      notionBlocks.push(...createBulletedListBlocks(listItems));
      i = j;
      continue;
    }
    
    // Process numbered lists
    if (line.match(/^\d+\. /)) {
      // Collect all list items
      const listItems = [];
      let j = i;
      
      while (j < lines.length && lines[j].trim().match(/^\d+\. /)) {
        listItems.push(lines[j].trim().replace(/^\d+\. /, ''));
        j++;
      }
      
      notionBlocks.push(...createNumberedListBlocks(listItems));
      i = j;
      continue;
    }
    
    // Process code blocks
    if (line.startsWith('```')) {
      const language = line.substring(3).trim();
      let code = '';
      let j = i + 1;
      
      while (j < lines.length && !lines[j].trim().startsWith('```')) {
        code += lines[j] + '\n';
        j++;
      }
      
      notionBlocks.push(createCodeBlock(code, language));
      i = j + 1; // Skip the closing ``` too
      continue;
    }
    
    // Process horizontal rules
    if (line.match(/^(\*\*\*|\-\-\-|\_\_\_)$/)) {
      notionBlocks.push(createDividerBlock());
      i++;
      continue;
    }
    
    // Process blockquotes
    if (line.startsWith('>')) {
      let quote = line.substring(1).trim();
      let j = i + 1;
      
      while (j < lines.length && lines[j].trim().startsWith('>')) {
        quote += '\n' + lines[j].substring(1).trim();
        j++;
      }
      
      notionBlocks.push(createQuoteBlock(quote));
      i = j;
      continue;
    }
    
    // Default: treat as paragraph
    notionBlocks.push(createParagraphBlock(line));
    i++;
  }
  
  return notionBlocks;
}

/**
 * Create a heading block for Notion API
 * 
 * @param {string} text - Heading text content
 * @param {number} level - Heading level (1-3)
 * @returns {Object} Notion heading block
 */
function createHeadingBlock(text, level) {
  // Map heading levels to Notion heading types
  const headingType = {
    1: 'heading_1',
    2: 'heading_2',
    3: 'heading_3',
  }[Math.min(level, 3)]; // Notion only supports h1-h3
  
  return {
    object: 'block',
    type: headingType,
    [headingType]: {
      rich_text: [
        {
          type: 'text',
          text: {
            content: text,
          },
        },
      ],
    },
  };
}

/**
 * Create a paragraph block for Notion API
 * 
 * @param {string} text - Paragraph text content
 * @returns {Object} Notion paragraph block
 */
function createParagraphBlock(text) {
  return {
    object: 'block',
    type: 'paragraph',
    paragraph: {
      rich_text: [
        {
          type: 'text',
          text: {
            content: text,
          },
        },
      ],
    },
  };
}

/**
 * Create bulleted list blocks for Notion API
 * 
 * @param {Array<string>} items - List items
 * @returns {Array<Object>} Array of Notion bulleted list item blocks
 */
function createBulletedListBlocks(items) {
  return items.map(item => ({
    object: 'block',
    type: 'bulleted_list_item',
    bulleted_list_item: {
      rich_text: [
        {
          type: 'text',
          text: {
            content: item,
          },
        },
      ],
    },
  }));
}

/**
 * Create numbered list blocks for Notion API
 * 
 * @param {Array<string>} items - List items
 * @returns {Array<Object>} Array of Notion numbered list item blocks
 */
function createNumberedListBlocks(items) {
  return items.map(item => ({
    object: 'block',
    type: 'numbered_list_item',
    numbered_list_item: {
      rich_text: [
        {
          type: 'text',
          text: {
            content: item,
          },
        },
      ],
    },
  }));
}

/**
 * Create a code block for Notion API
 * 
 * @param {string} code - Code content
 * @param {string} language - Programming language
 * @returns {Object} Notion code block
 */
function createCodeBlock(code, language) {
  return {
    object: 'block',
    type: 'code',
    code: {
      rich_text: [
        {
          type: 'text',
          text: {
            content: code,
          },
        },
      ],
      language: language || 'plain text',
    },
  };
}

/**
 * Create a divider block for Notion API
 * 
 * @returns {Object} Notion divider block
 */
function createDividerBlock() {
  return {
    object: 'block',
    type: 'divider',
    divider: {},
  };
}

/**
 * Create a quote block for Notion API
 * 
 * @param {string} text - Quote content
 * @returns {Object} Notion quote block
 */
function createQuoteBlock(text) {
  return {
    object: 'block',
    type: 'quote',
    quote: {
      rich_text: [
        {
          type: 'text',
          text: {
            content: text,
          },
        },
      ],
    },
  };
}

/**
 * Process the full markdown content and convert to Notion blocks
 * This handles the specific format of the Google Keep exports
 * 
 * @param {string} content - Full markdown content
 * @returns {Array} Array of Notion blocks
 */
export function processMarkdownContent(content) {
  // Extract metadata if present
  const metaSection = content.match(/\*\*Created:\*\*.*?\*\*Labels:\*\*.*?\n\s*---\n/s);
  
  // If metadata exists, create a separate callout block for it
  const blocks = [];
  
  if (metaSection) {
    const metaText = metaSection[0].trim();
    blocks.push({
      object: 'block',
      type: 'callout',
      callout: {
        rich_text: [
          {
            type: 'text',
            text: {
              content: metaText,
            },
          },
        ],
        icon: {
          emoji: 'ℹ️',
        },
        color: 'gray_background',
      },
    });
    
    // Remove metadata from content for further processing
    content = content.replace(metaSection[0], '');
  }
  
  // Process the rest of the content
  const contentBlocks = convertMarkdownToNotionBlocks(content);
  blocks.push(...contentBlocks);
  
  return blocks;
}

export default {
  convertMarkdownToNotionBlocks,
  processMarkdownContent,
};
