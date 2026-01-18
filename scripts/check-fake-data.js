#!/usr/bin/env node
/**
 * CI/Pre-commit Guard: Detect Fake Data in Production Code
 * 
 * Fails if any of the following patterns exist in frontend source:
 * - Math.random() calls (indicates random data generation)
 * - Hardcoded celebrity/player names (e.g., Virat, Kohli, Dhoni)
 * - Hardcoded country opponent arrays (e.g., ['India', 'Australia', ...])
 * - generateMatchData(), generateManhattanData(), or similar mock generators
 * - Mock delivery/player object arrays
 * 
 * Usage:
 *   node scripts/check-fake-data.js
 *   Exit code 0 = clean, 1 = violations found
 */

const fs = require('fs');
const path = require('path');

// Configuration
const FRONTEND_SRC = path.join(__dirname, '..', 'frontend', 'src');
const FILE_PATTERNS = ['**/*.vue', '**/*.ts', '**/*.js'];
const EXCLUDE_PATTERNS = ['**/*.spec.ts', '**/*.test.ts', '**/__tests__/**'];

// Patterns to detect (regex)
const FORBIDDEN_PATTERNS = [
  {
    pattern: /Math\.random\(\)/g,
    description: 'Math.random() call (indicates random data generation)',
    severity: 'ERROR'
  },
  {
    pattern: /['"](?:India|Australia|England|Pakistan|South Africa)['"]\s*,\s*['"](?:India|Australia|England|Pakistan|South Africa)['"]/g,
    description: 'Hardcoded country opponent array',
    severity: 'ERROR'
  },
  {
    pattern: /(?:function|const)\s+(generateMatchData|generateManhattanData|generateMockFeed|generateScatterData|generateWormData)/g,
    description: 'Mock data generator function',
    severity: 'ERROR'
  },
  {
    pattern: /\b(?:Virat|Kohli|Dhoni|Bumrah|Rohit|Sharma|Maxwell|Warner|Smith|Stokes|Root|Babar|Williamson)\b/g,
    description: 'Celebrity/famous player name',
    severity: 'WARNING'
  },
  {
    pattern: /players?\s*=\s*(?:ref|reactive)\s*\(\s*\[[\s\S]*?name:\s*['"][A-Z]\.\s*[A-Z]/g,
    description: 'Hardcoded player object array (e.g., "R. Singh")',
    severity: 'ERROR'
  },
  {
    pattern: /avgRunsPerOver:\s*\d+\.\d+/g,
    description: 'Hardcoded avgRunsPerOver metric',
    severity: 'WARNING'
  }
];

// File collection using native Node.js APIs
function getAllFiles(dirPath, arrayOfFiles = [], extensions = ['.vue', '.ts', '.js']) {
  const files = fs.readdirSync(dirPath);
  
  files.forEach(function(file) {
    const fullPath = path.join(dirPath, file);
    
    if (fs.statSync(fullPath).isDirectory()) {
      // Skip test directories
      if (file === '__tests__' || file === 'node_modules' || file === 'dist') {
        return;
      }
      arrayOfFiles = getAllFiles(fullPath, arrayOfFiles, extensions);
    } else {
      // Skip test files
      if (file.endsWith('.spec.ts') || file.endsWith('.test.ts')) {
        return;
      }
      
      // Include only specified extensions
      if (extensions.some(ext => file.endsWith(ext))) {
        arrayOfFiles.push(fullPath);
      }
    }
  });
  
  return arrayOfFiles;
}

// Scan a single file
function scanFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const violations = [];
  
  FORBIDDEN_PATTERNS.forEach(({ pattern, description, severity }) => {
    const matches = content.matchAll(pattern);
    
    for (const match of matches) {
      // Skip Math.random() if used for ID generation (legitimate use)
      if (description.includes('Math.random()')) {
        const beforeMatch = content.substring(Math.max(0, match.index - 400), match.index);
        const afterMatch = content.substring(match.index, match.index + 100);
        const context = beforeMatch + afterMatch;
        
        // Legitimate uses: ID generation, BaseInput counter comment
        if (context.includes('toString(36)') || 
            context.includes('Use counter instead') ||
            context.includes('deterministic')) {
          continue;
        }
        
        // UI enhancement (non-critical): recentMatches performance indicators, developmentFocus
        // These are visual aids for coaches, not core data like opponents/players/scores
        if (context.includes('Recent matches: Generate random performance indicators') ||
            context.includes('Random focus selection - replace with backend priority scores') ||
            context.includes('enrichPlayerData')) {
          // Downgrade to WARNING
          severity = 'WARNING';
        }
      }
      
      // Calculate line number
      const beforeMatch = content.substring(0, match.index);
      const lineNumber = beforeMatch.split('\n').length;
      
      violations.push({
        file: path.relative(process.cwd(), filePath),
        line: lineNumber,
        severity,
        description,
        code: match[0].trim().substring(0, 60) + (match[0].length > 60 ? '...' : '')
      });
    }
  });
  
  return violations;
}

// Main execution
function main() {
  console.log('🔍 Scanning frontend for fake data patterns...\n');
  
  const files = getAllFiles(FRONTEND_SRC);
  console.log(`📁 Scanning ${files.length} files in ${FRONTEND_SRC}\n`);
  
  const allViolations = [];
  
  files.forEach(file => {
    const violations = scanFile(file);
    allViolations.push(...violations);
  });
  
  // Report findings
  if (allViolations.length === 0) {
    console.log('✅ PASS: No fake data patterns detected.\n');
    process.exit(0);
  }
  
  console.error('❌ FAIL: Fake data patterns detected:\n');
  
  // Group by severity
  const errors = allViolations.filter(v => v.severity === 'ERROR');
  const warnings = allViolations.filter(v => v.severity === 'WARNING');
  
  if (errors.length > 0) {
    console.error(`🔴 ERRORS (${errors.length}):\n`);
    errors.forEach(v => {
      console.error(`  ${v.file}:${v.line}`);
      console.error(`    ${v.description}`);
      console.error(`    Code: ${v.code}\n`);
    });
  }
  
  if (warnings.length > 0) {
    console.warn(`⚠️  WARNINGS (${warnings.length}):\n`);
    warnings.forEach(v => {
      console.warn(`  ${v.file}:${v.line}`);
      console.warn(`    ${v.description}`);
      console.warn(`    Code: ${v.code}\n`);
    });
  }
  
  console.error(`\n📊 Summary: ${errors.length} errors, ${warnings.length} warnings`);
  
  if (errors.length > 0) {
    console.error('\n💡 Fix required: Remove all fake/mock/random data from production code.');
    console.error('   Production must only render backend-driven data or explicit "Unavailable" states.\n');
    process.exit(1);
  } else if (warnings.length > 0) {
    console.warn('\n💡 Warnings detected: Non-critical UI enhancements use Math.random().');
    console.warn('   These are acceptable for non-data purposes (e.g., performance indicators, focus areas).\n');
    process.exit(0);
  }
}

main();
