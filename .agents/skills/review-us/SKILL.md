---
name: review-us
description: >
  Comprehensive user story validation skill that orchestrates code review and test automation.
  This skill should be used after completing a user story implementation to validate code quality,
  security, and test coverage. It analyzes changed files via git diff, runs code-reviewer and
  test-automator agents, and produces a consolidated approval checklist. Invoke with /review-us.
---

# User Story Review & Validation

This skill validates user story implementations by orchestrating two specialized agents in sequence:
1. **Code Reviewer** - Static analysis, security, performance, and best practices
2. **Test Automator** - Test coverage, quality, and missing test cases

## Workflow

### Phase 1: Gather Context

1. Run `git diff --name-only` to identify changed files
2. Run `git diff --stat` for a summary of changes
3. Categorize files by type (frontend, backend, tests, config)

### Phase 2: Code Review

Launch the `code-reviewer` agent with focus on:

**Security Analysis:**
- OWASP Top 10 vulnerabilities (injection, XSS, CSRF, etc.)
- Input validation and sanitization
- Authentication and authorization checks
- Secrets exposure (API keys, credentials in code)
- SQL/NoSQL injection vectors
- Path traversal and file access issues

**Code Quality:**
- Clean code principles and readability
- SOLID principles adherence
- Code complexity (cyclomatic complexity, nesting depth)
- Error handling patterns
- Logging and observability
- Performance considerations (N+1 queries, memory leaks)

**Best Practices:**
- Framework-specific patterns (React hooks, FastAPI dependencies)
- Type safety (TypeScript strict mode, Python type hints)
- Async/await correctness
- Resource cleanup (connections, file handles)
- Configuration management

### Phase 3: Test Validation

Launch the `test-automator` agent with focus on:

**CRITICAL REQUIREMENT: Real Data Testing**

Mocks alone are NOT sufficient. Every user story MUST include tests with real data:

- **Integration tests with real database** - Test actual DB operations, not mocked queries
- **API tests with real HTTP calls** - Use httpx/requests to hit actual endpoints
- **E2E tests with real browser** - Playwright/Cypress testing real user flows
- **Real external services** - Use test/sandbox environments (Stripe test mode, etc.)

Flag as **CRITICAL** if:
- All tests are mocked with no real data validation
- No integration tests exist for new API endpoints
- Database operations are only tested with mocks
- External service integrations have no real API tests

**Test Pyramid (Required Balance):**
```
        /\
       /E2E\        <- Real browser, real data (fewer but critical)
      /------\
     /Integr. \     <- Real DB, real APIs (must exist!)
    /----------\
   /   Unit     \   <- Can use mocks (but not exclusively)
  /--------------\
```

**Coverage Analysis:**
- Unit test coverage for new/changed code
- Integration test coverage for API endpoints (WITH REAL DATA)
- E2E test coverage for user flows (WITH REAL BROWSER)
- Edge cases and error paths covered

**Test Quality:**
- Mocks used appropriately (external services in unit tests only)
- Integration tests use real database connections
- E2E tests run against real or staging environment
- Assertions are meaningful (not just "no errors")
- Test naming follows conventions
- Setup/teardown properly implemented (real data cleanup!)
- Async tests handled correctly

**Missing Tests - Flag These:**
- No integration tests for new endpoints = **CRITICAL**
- No E2E test for new user flow = **HIGH**
- Only mocked DB tests = **CRITICAL**
- No real API calls to external services = **HIGH**
- Missing edge case coverage = **MEDIUM**

### Phase 4: Generate Report

Create consolidated output with:

1. **Inline Checklist** - Quick pass/fail summary in terminal
2. **Markdown Report** - Detailed findings saved to `reviews/review-{timestamp}.md`

## Output Format

### Inline Checklist

```
## User Story Review Summary

### Code Review
- [ ] Security: No vulnerabilities found
- [ ] Quality: Code follows best practices
- [ ] Performance: No obvious bottlenecks
- [ ] Types: Proper type coverage

### Test Coverage
- [ ] Unit Tests: Adequate coverage
- [ ] Integration Tests: Real DB/API calls (NOT just mocks!)
- [ ] E2E Tests: Real browser testing user flows
- [ ] Real Data: Tests use actual data, not just mocks
- [ ] Edge Cases: Error paths covered

### Issues Found
- [CRITICAL] Description of critical issue
- [HIGH] Description of high priority issue
- [MEDIUM] Description of medium issue
- [LOW] Description of low priority issue

### Verdict: APPROVED / NEEDS WORK
```

### Markdown Report Structure

```markdown
# User Story Review Report

**Date:** {timestamp}
**Files Changed:** {count}
**Verdict:** {APPROVED | NEEDS WORK}

## Changed Files
- path/to/file1.ts (added)
- path/to/file2.py (modified)

## Code Review Findings

### Security
{detailed findings}

### Code Quality
{detailed findings}

### Performance
{detailed findings}

## Test Coverage Analysis

### Current Coverage
{coverage metrics if available}

### Missing Tests
{list of suggested tests}

### Test Quality Issues
{any problems with existing tests}

## Action Items
1. {specific action to take}
2. {specific action to take}

## Approval Checklist
- [ ] All critical issues resolved
- [ ] All high priority issues resolved
- [ ] Integration tests with real data exist
- [ ] E2E tests cover new user flows
- [ ] No mock-only test suites
- [ ] No security vulnerabilities
```

## Execution Instructions

1. **Do not** modify any code - only analyze and report
2. **Do** provide specific file paths and line numbers for issues
3. **Do** prioritize issues by severity (CRITICAL > HIGH > MEDIUM > LOW)
4. **Do** suggest specific fixes without implementing them
5. **Do** create the report file in a `reviews/` directory (create if needed)
6. **Do** provide actionable feedback that can be addressed immediately

## Agent Orchestration

To execute this skill:

1. First, gather git diff information using Bash
2. Launch `code-reviewer` agent via Task tool with the list of changed files
3. Launch `test-automator` agent via Task tool with the same context
4. Consolidate findings from both agents
5. Generate inline summary and markdown report
6. Provide clear verdict: APPROVED or NEEDS WORK

## Severity Definitions

- **CRITICAL**: Security vulnerabilities, data loss risks, breaking changes
- **HIGH**: Bugs, missing validation, significant code smells
- **MEDIUM**: Code quality issues, minor performance concerns
- **LOW**: Style issues, suggestions for improvement
