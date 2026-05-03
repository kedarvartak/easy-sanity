from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse


DOMAIN_SUMMARY_SCRIPT = """
() => {
    function safeText(value, limit = 120) {
        return (value || '').replace(/\\s+/g, ' ').trim().slice(0, limit);
    }

    function visibleElements(selector) {
        return Array.from(document.querySelectorAll(selector)).filter((el) => {
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
        });
    }

    function inferCardElements() {
        return visibleElements(
            '[data-testid*="card" i], [class*="card" i], article, section[class*="tile" i], section[class*="panel" i]'
        ).slice(0, 20);
    }

    function findWorkflowStep() {
        const activeStep = document.querySelector(
            '[aria-current="step"], [data-step].active, [role="tab"][aria-selected="true"], .step.active, .wizard-step.active'
        );
        if (activeStep) {
            return safeText(activeStep.innerText || activeStep.textContent || activeStep.getAttribute('aria-label') || '', 160);
        }

        const progressLike = Array.from(document.querySelectorAll('progress, [role="progressbar"], [aria-current="page"]'))
            .map((el) => safeText(el.innerText || el.textContent || el.getAttribute('aria-label') || '', 160))
            .filter(Boolean);
        if (progressLike.length) {
            return progressLike[0];
        }

        const heading = document.querySelector('main h1, h1, [role="main"] h1, [role="heading"][aria-level="1"]');
        if (heading) {
            return safeText(heading.innerText || heading.textContent || '', 160);
        }
        return '';
    }

    const headings = visibleElements('h1, h2, h3, [role="heading"]').slice(0, 12).map((el) => ({
        level: el.tagName.toLowerCase().startsWith('h') ? el.tagName.toLowerCase() : (el.getAttribute('aria-level') || 'heading'),
        text: safeText(el.innerText || el.textContent || '', 160),
    })).filter((item) => item.text);

    const forms = visibleElements('form').slice(0, 12).map((form, index) => {
        const fields = Array.from(form.querySelectorAll('input, select, textarea')).slice(0, 20).map((field) => {
            const label = field.labels && field.labels.length
                ? Array.from(field.labels).map((el) => safeText(el.innerText || el.textContent || '', 80)).join(' ')
                : safeText(
                    document.querySelector(`label[for="${field.id}"]`)?.innerText ||
                    document.querySelector(`label[for="${field.id}"]`)?.textContent ||
                    '',
                    80
                );
            return {
                tag: field.tagName.toLowerCase(),
                type: field.getAttribute('type') || '',
                name: field.getAttribute('name') || '',
                id: field.id || '',
                label,
                placeholder: safeText(field.getAttribute('placeholder') || '', 80),
                required: !!field.required,
                disabled: !!field.disabled,
            };
        });

        const submitButtons = Array.from(form.querySelectorAll('button, input[type="submit"]')).slice(0, 5).map((button) => ({
            text: safeText(button.innerText || button.textContent || button.getAttribute('value') || '', 80),
            type: button.getAttribute('type') || '',
        }));

        return {
            index,
            id: form.id || '',
            name: form.getAttribute('name') || '',
            aria_label: form.getAttribute('aria-label') || '',
            field_count: fields.length,
            fields,
            submit_buttons: submitButtons,
        };
    });

    const navs = visibleElements('nav, [role="navigation"]').slice(0, 8).map((nav, index) => ({
        index,
        label: safeText(nav.getAttribute('aria-label') || '', 80),
        links: Array.from(nav.querySelectorAll('a')).slice(0, 8).map((link) => safeText(link.innerText || link.textContent || '', 80)).filter(Boolean),
    }));

    const dialogs = visibleElements('dialog, [role="dialog"], [aria-modal="true"]').slice(0, 8).map((dialog, index) => ({
        index,
        title: safeText(
            dialog.querySelector('h1, h2, h3, [role="heading"]')?.innerText ||
            dialog.querySelector('h1, h2, h3, [role="heading"]')?.textContent ||
            dialog.getAttribute('aria-label') ||
            '',
            120
        ),
        text: safeText(dialog.innerText || dialog.textContent || '', 200),
    }));

    const tables = visibleElements('table, [role="table"], [data-testid*="table" i]').slice(0, 10).map((table, index) => {
        const headers = Array.from(table.querySelectorAll('th')).slice(0, 8).map((th) => safeText(th.innerText || th.textContent || '', 60)).filter(Boolean);
        const rows = table.querySelectorAll('tbody tr, [role="row"]').length;
        return {
            index,
            headers,
            row_count: rows,
        };
    });

    const cards = inferCardElements().map((card, index) => ({
        index,
        title: safeText(
            card.querySelector('h1, h2, h3, h4, [role="heading"]')?.innerText ||
            card.querySelector('h1, h2, h3, h4, [role="heading"]')?.textContent ||
            '',
            120
        ),
        text: safeText(card.innerText || card.textContent || '', 160),
    }));

    const alerts = visibleElements('[role="alert"], .alert, .toast, [data-testid*="alert" i], [data-testid*="toast" i]')
        .slice(0, 10)
        .map((el, index) => ({
            index,
            text: safeText(el.innerText || el.textContent || '', 160),
        }))
        .filter((item) => item.text);

    const primaryActions = visibleElements('button, a, [role="button"]').slice(0, 12).map((el, index) => ({
        index,
        tag: el.tagName.toLowerCase(),
        text: safeText(el.innerText || el.textContent || el.getAttribute('aria-label') || '', 80),
        href: el.getAttribute('href') || '',
    })).filter((item) => item.text || item.href);

    return {
        title: document.title || '',
        url: window.location.href,
        path: window.location.pathname,
        query_keys: Array.from(new URLSearchParams(window.location.search).keys()).slice(0, 12),
        workflow_step: findWorkflowStep(),
        headings,
        forms,
        navs,
        dialogs,
        tables,
        cards,
        alerts,
        primary_actions: primaryActions,
        counts: {
            forms: forms.length,
            fields: forms.reduce((total, form) => total + form.field_count, 0),
            navs: navs.length,
            dialogs: dialogs.length,
            tables: tables.length,
            cards: cards.length,
            alerts: alerts.length,
        },
    };
}
"""


async def capture_domain_summary(page) -> dict[str, Any]:
    return await page.evaluate(DOMAIN_SUMMARY_SCRIPT)


def summarize_domain_summary(summary: dict[str, Any]) -> str:
    path = summary.get("path") or "/"
    workflow = summary.get("workflow_step") or "no explicit workflow step detected"
    counts = summary.get("counts", {})
    return (
        f"Path {path}. Workflow context: {workflow}. "
        f"Forms: {counts.get('forms', 0)}, tables: {counts.get('tables', 0)}, "
        f"dialogs: {counts.get('dialogs', 0)}, cards: {counts.get('cards', 0)}, "
        f"alerts: {counts.get('alerts', 0)}."
    )


def domain_snapshot_signature(summary: dict[str, Any]) -> str:
    reduced = {
        "path": summary.get("path"),
        "title": summary.get("title"),
        "workflow_step": summary.get("workflow_step"),
        "counts": summary.get("counts", {}),
        "headings": [item.get("text") for item in summary.get("headings", [])[:6]],
        "alerts": [item.get("text") for item in summary.get("alerts", [])[:4]],
    }
    return json.dumps(reduced, sort_keys=True)


def infer_route_context(summary: dict[str, Any]) -> dict[str, Any]:
    parsed = urlparse(summary.get("url", ""))
    segments = [segment for segment in parsed.path.split("/") if segment]
    return {
        "path": summary.get("path") or parsed.path or "/",
        "segments": segments,
        "query_keys": summary.get("query_keys", []),
        "likely_surface": segments[-1] if segments else "home",
    }


def summarize_domain_changes(previous: dict[str, Any] | None, current: dict[str, Any]) -> list[str]:
    if not previous:
        return [f"Initial page snapshot captured for {current.get('path') or '/'}."]

    changes: list[str] = []
    if previous.get("path") != current.get("path"):
        changes.append(f"Route changed from {previous.get('path') or '/'} to {current.get('path') or '/'}.")
    if previous.get("title") != current.get("title"):
        changes.append("Page title changed.")
    if previous.get("workflow_step") != current.get("workflow_step") and current.get("workflow_step"):
        changes.append(f"Workflow step is now '{current.get('workflow_step')}'.")

    previous_counts = previous.get("counts", {})
    current_counts = current.get("counts", {})
    for key in ("forms", "dialogs", "tables", "cards", "alerts"):
        if previous_counts.get(key) != current_counts.get(key):
            changes.append(f"{key.title()} count changed from {previous_counts.get(key, 0)} to {current_counts.get(key, 0)}.")

    previous_alerts = [item.get("text") for item in previous.get("alerts", [])]
    current_alerts = [item.get("text") for item in current.get("alerts", [])]
    new_alerts = [text for text in current_alerts if text and text not in previous_alerts]
    if new_alerts:
        changes.append(f"New alert or toast content appeared: {new_alerts[0]}")

    previous_headings = [item.get("text") for item in previous.get("headings", [])]
    current_headings = [item.get("text") for item in current.get("headings", [])]
    new_headings = [text for text in current_headings if text and text not in previous_headings]
    if new_headings:
        changes.append(f"New heading detected: {new_headings[0]}")

    if not changes:
        changes.append("No major semantic page changes detected.")
    return changes
