# Phase Transition Checklist

Use this checklist when completing a phase and starting the next one.

## Before Starting a New Phase

- [ ] Review the current phase documentation one final time
- [ ] Ensure all phase tasks are completed
- [ ] Test and validate all work from current phase
- [ ] Document any issues encountered and their resolutions

## Phase Completion Steps

### 1. Update IMPLEMENTATION_TRACKER.md

- [ ] Mark completed phase status as `✅ COMPLETE` in Phase Status Overview table
- [ ] Add completion date to the table
- [ ] Update the detailed phase section with:
  - [ ] Final status: `**Status**: ✅ COMPLETE`
  - [ ] Completion date
  - [ ] Summary of what was accomplished
  - [ ] Any final validation results
- [ ] Add entry to Daily Notes section with:
  - [ ] Date
  - [ ] Phase completed
  - [ ] Key accomplishments
  - [ ] Any important findings
- [ ] Update Issues & Resolutions Log if any new issues were encountered
- [ ] Update Sign-off table with completion date
- [ ] Update "Last Updated" date at bottom
- [ ] Update "Next Action" to reference new phase

### 2. Update CURRENT_PHASE.md

- [ ] Change phase number in title (e.g., "Phase 2" → "Phase 3")
- [ ] Update phase name/description
- [ ] Update Status line (⏳ Ready to Start, 🔄 In Progress, etc.)
- [ ] Update VM IP if it changed
- [ ] Update "Full Phase Documentation" link to new phase file
- [ ] Update "Quick Start" section with new phase commands
- [ ] Replace all task checkboxes with new phase tasks
- [ ] Update "Previous Phase" link to completed phase
- [ ] Update "Next Phase" link to following phase
- [ ] Update "Last Updated" date

### 3. Update docs/README.md

- [ ] Mark completed phase with ✅ in "Phase Documentation" list
- [ ] Mark new current phase with ⏳
- [ ] Update "Current Status" section:
  - [ ] Update completed phase
  - [ ] Update current phase
- [ ] Update "Quick Start for Current Phase" section
- [ ] Update VM IP if changed

### 4. Prepare for New Phase

- [ ] Read the new phase documentation: `docs/phases/Phase_X_*.md`
- [ ] Review requirements and prerequisites
- [ ] Ensure all dependencies from previous phases are met
- [ ] Prepare any required credentials or access
- [ ] Review Common Commands section in CLAUDE.md for the new phase

## Verification

After updating all files, verify:

- [ ] `@CURRENT_PHASE.md` opens correctly and shows new phase
- [ ] `@IMPLEMENTATION_TRACKER.md` shows completed phase as ✅
- [ ] `docs/README.md` navigation is correct
- [ ] All links in updated files work correctly
- [ ] Phase documentation file exists for new phase

## Template for Daily Notes Entry

```markdown
### YYYY-MM-DD (Phase X COMPLETED / Phase Y STARTED)
- **Phase X Completed**: [Brief summary of accomplishments]
- **Key Achievements**:
  - [Achievement 1]
  - [Achievement 2]
- **Technical Details**:
  - [Important technical finding 1]
  - [Important technical finding 2]
- **Status**:
  - Phase X: ✅ Complete
  - Phase Y: ⏳ Starting
  - [Any other relevant status updates]
```

## Quick Commands for Phase Transition

```bash
# View current phase
cat CURRENT_PHASE.md

# Check implementation tracker
cat IMPLEMENTATION_TRACKER.md | grep "Phase X"

# Read new phase documentation
cat docs/phases/Phase_X_*.md

# View documentation index
cat docs/README.md
```

---

**Remember**: Keeping documentation updated ensures smooth handoffs between sessions and prevents loss of progress!
