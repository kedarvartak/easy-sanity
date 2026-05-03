TASK_EXECUTION_PROMPT_TEMPLATE = """Execute the following browser automation task using the available browser tools.

Task: {task_prompt}

Steps to follow:
1. Call browser_start with the task description
2. Use browser_navigate to go to the required URL
3. Call browser_get_state frequently to see the current page and screenshot
4. Use browser_click, browser_type, browser_scroll, browser_fill, and browser_click_by_role as needed
5. Use browser_find_element when you need help identifying the right interactive element
6. Use browser_extract to pull out data when required
7. Call browser_stop with a summary when the task is complete"""


FIND_ELEMENT_RESULT_MESSAGE = (
    "Use the returned label, text, role, id, or name with higher-level browser tools."
)


FILL_FIELD_NOT_FOUND_TEMPLATE = (
    "Could not find a field matching '{field}'. Try browser_find_element first."
)


TASK_WIZARD_PROMPT_TEMPLATE = """Complete the following browser sanity task:

Goal: {goal}

Suggested structure:
1. Call browser_start with a clear task name.
2. Navigate to {start_url}.
3. Use browser_get_state to inspect the page before acting.
4. Perform the required interactions step by step.
5. Use assertions or explicit verification steps to confirm the expected outcome.
6. End with browser_stop and summarize whether the task passed.

Suggested task prompt:
{task_prompt}
"""
