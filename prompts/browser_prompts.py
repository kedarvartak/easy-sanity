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
