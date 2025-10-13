/**
 * INI File Parser and Generator
 * Handles parsing and generation of .config files in INI format
 * Compatible with Python ConfigParser format used in desktop application
 */

/**
 * Parse INI format string into structured object
 * @param {string} fileContent - The raw INI file content
 * @returns {Object} Parsed configuration with sections as keys
 *
 * Example output:
 * {
 *   DEFAULT: { city_size: '16', vehicle_count: '4', ... },
 *   ANIMATION: { animation_style: 'terminal_map', ... },
 *   ...
 * }
 */
export function parseINI(fileContent) {
  const result = {};
  let currentSection = "DEFAULT";

  // Initialize DEFAULT section
  result[currentSection] = {};

  const lines = fileContent.split("\n");

  for (let line of lines) {
    // Remove leading/trailing whitespace
    line = line.trim();

    // Skip empty lines
    if (line.length === 0) continue;

    // Skip comment lines (start with # or ;)
    if (line.startsWith("#") || line.startsWith(";")) continue;

    // Check for section header [SECTION_NAME]
    if (line.startsWith("[") && line.endsWith("]")) {
      currentSection = line.slice(1, -1).trim();
      result[currentSection] = {};
      continue;
    }

    // Parse key-value pair
    const equalIndex = line.indexOf("=");
    if (equalIndex > 0) {
      const key = line.slice(0, equalIndex).trim();
      let value = line.slice(equalIndex + 1).trim();

      // Remove inline comments (value before # or ;)
      const commentIndex = value.search(/\s+[#;]/);
      if (commentIndex >= 0) {
        value = value.slice(0, commentIndex).trim();
      }

      // Store the value (empty string if value is empty)
      result[currentSection][key] = value;
    }
  }

  return result;
}

/**
 * Generate INI format string from structured object
 * @param {Object} sections - Configuration object with sections
 * @returns {string} INI formatted string
 *
 * Example input:
 * {
 *   DEFAULT: { city_size: 16, vehicle_count: 4 },
 *   ANIMATION: { animation_style: 'terminal_map' }
 * }
 */
export function generateINI(sections) {
  const lines = [];

  // Process each section
  for (const [sectionName, sectionData] of Object.entries(sections)) {
    // Add blank line before section (except for first section)
    if (lines.length > 0) {
      lines.push("");
    }

    // Add section header
    lines.push(`[${sectionName}]`);
    lines.push("");

    // Add key-value pairs
    for (const [key, value] of Object.entries(sectionData)) {
      // Handle different value types
      let valueStr;
      if (value === null || value === undefined || value === "") {
        valueStr = "";
      } else if (typeof value === "boolean") {
        valueStr = value ? "True" : "False";
      } else {
        valueStr = String(value);
      }

      lines.push(`${key} = ${valueStr}`);
    }
  }

  // Join with newlines and ensure trailing newline
  return lines.join("\n") + "\n";
}

/**
 * Parse a single INI value to appropriate JavaScript type
 * @param {string} value - The string value from INI file
 * @returns {*} Parsed value (string, number, boolean, or null)
 */
export function parseValue(value) {
  // Handle empty values
  if (value === "" || value === null || value === undefined) {
    return null;
  }

  // Handle boolean values (case-insensitive)
  const lowerValue = value.toLowerCase();
  if (lowerValue === "true") return true;
  if (lowerValue === "false") return false;

  // Try to parse as number
  const numValue = Number(value);
  if (!isNaN(numValue) && value.trim() !== "") {
    return numValue;
  }

  // Return as string
  return value;
}

/**
 * Get value from parsed INI with type conversion and default fallback
 * @param {Object} parsedINI - Parsed INI object
 * @param {string} section - Section name
 * @param {string} key - Key name
 * @param {*} defaultValue - Default value if not found
 * @returns {*} Value with appropriate type
 */
export function getINIValue(parsedINI, section, key, defaultValue = null) {
  if (!parsedINI[section] || parsedINI[section][key] === undefined) {
    return defaultValue;
  }

  const value = parsedINI[section][key];
  return parseValue(value);
}
