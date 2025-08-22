### Improvements Checklist
- [ ] **Critical**: Implement a reliable automated test for the generic `Exception` handler. The current test is skipped, which leaves a critical part of the error handling untested.
- [ ] Implement or clean up `packages/backend/api/campaign_api.py` commented-out placeholder code.
- [ ] Consider adding a linter rule to catch unused imports in CI
- [ ] Enable AIAPIError test in `tests/integration/backend/test_error_handler.py` once implemented.
- [ ] Consider adding integration tests for real Discord interactions (from 2.3 review)

Validate 3.2,3,4 and then recheck any remaining tasks