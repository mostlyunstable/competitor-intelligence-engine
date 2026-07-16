from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from app.parsers.strategy import ParsedResult, ParsingStrategy

_LOGIN_KWS = frozenset(
    {
        "login",
        "signin",
        "sign-in",
        "signup",
        "sign-up",
        "register",
        "create account",
        "log in",
        "log-in",
    }
)

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

_CITY_KWS = frozenset(
    {
        "city",
        "location",
        "area",
        "region",
        "state",
        "province",
        "district",
        "zone",
        "sector",
        "ward",
    }
)
_CATEGORY_KWS = frozenset(
    {
        "service",
        "category",
        "type",
        "what",
        "need",
        "help with",
        "issue",
        "problem",
        "department",
        "purpose",
        "inquiry",
        "subject",
    }
)
_CONTACT_KWS = frozenset({"contact", "method", "referral", "heard about", "how did you"})
_EMAIL_KWS = frozenset({"email", "e-mail", "mail"})
_PHONE_KWS = frozenset(
    {"phone", "tel", "mobile", "telephone", "cell", "contact number", "phone number"}
)
_NAME_KWS = frozenset({"name", "first", "last", "full name"})
_MESSAGE_KWS = frozenset(
    {"message", "detail", "description", "comment", "note", "additional", "request"}
)


def _get_label_for_input(inp: Tag, form: Tag) -> str:
    """Resolve the visible label text for an input element."""
    input_id = inp.get("id")
    if input_id:
        html_root = form.find_parent("html") or form
        found_label = (
            html_root.find("label", attrs={"for": input_id}) if isinstance(html_root, Tag) else None
        )
        if found_label and isinstance(found_label, Tag):
            text = found_label.get_text(" ", strip=True)
            if text:
                return text

    parent_label = inp.find_parent("label")
    if parent_label:
        text = parent_label.get_text(" ", strip=True)
        exclude = inp.get_text(" ", strip=True)
        if exclude:
            text = text.replace(exclude, "", 1).strip()
        if text:
            return text

    aria = inp.get("aria-label")
    if aria and isinstance(aria, str) and aria.strip():
        return aria.strip()

    placeholder = inp.get("placeholder")
    if placeholder and isinstance(placeholder, str) and placeholder.strip():
        return placeholder.strip()

    return ""


def _get_label_text(inp: Tag, form: Tag) -> str:
    """Return the resolved label in lowercase."""
    return _get_label_for_input(inp, form).lower()


def _is_login_form(form: Tag) -> bool:
    """Return True if the form appears to be a login/signup form."""
    if form.find("input", attrs={"type": "password"}):
        return True
    action = str(form.get("action", "") or "").lower()
    for kw in _LOGIN_KWS:
        if kw in action:
            return True
    form_id = str(form.get("id", "") or "").lower()
    for kw in _LOGIN_KWS:
        if kw in form_id:
            return True
    form_class = " ".join(form.get("class") or []).lower()
    for kw in _LOGIN_KWS:
        if kw in form_class:
            return True
    submit = form.find("button", attrs={"type": "submit"}) or form.find(
        "input", attrs={"type": "submit"}
    )
    if submit:
        btn_text = submit.get_text(" ", strip=True).lower() or str(submit.get("value", "")).lower()
        for kw in _LOGIN_KWS:
            if kw in btn_text:
                return True
    return False


def _collect_select_options(select: Tag) -> list[str]:
    """Return all non-empty option texts from a select element."""
    options: list[str] = []
    for opt in select.find_all("option"):
        text = opt.get_text(strip=True)
        val = str(opt.get("value", "") or "").strip()
        if text and text.lower() not in (
            "select",
            "choose",
            "select one",
            "choose one",
            "--",
            "none",
            "",
        ):
            options.append(text)
        elif val and val.lower() not in (
            "select",
            "choose",
            "select one",
            "choose one",
            "--",
            "none",
            "",
        ):
            options.append(val)
    return options


def _collect_radio_checkbox_options(container: Tag) -> list[str]:
    """Return labels for radio/checkbox options in a group."""
    options: list[str] = []
    for inp in container.find_all(["input", "label"]):
        if inp.name == "input" and inp.get("type") in ("radio", "checkbox"):
            lbl = _get_label_for_input(inp, container)
            if lbl and lbl not in ("",):
                options.append(lbl)
        elif inp.name == "label":
            text = inp.get_text(" ", strip=True)
            inner_input = inp.find("input")
            if inner_input and text:
                exclude = inner_input.get_text(" ", strip=True)
                if exclude:
                    text = text.replace(exclude, "", 1).strip()
            if text and len(text) > 1:
                options.append(text)
    return list(dict.fromkeys(options))


def _classify_field(label: str, inp: Tag) -> str:
    """Classify a form field into a semantic type."""
    lower = label
    input_type = str(inp.get("type", "") or "").lower()
    input_name = str(inp.get("name", "") or "").lower()

    if input_type == "email":
        return "email"
    if input_type == "tel":
        return "phone"
    if input_type == "password":
        return "ignore"

    for kw in _CITY_KWS:
        if kw in lower or kw in input_name:
            return "city"
    for kw in _CATEGORY_KWS:
        if kw in lower or kw in input_name:
            return "category"
    for kw in _EMAIL_KWS:
        if kw in lower or kw in input_name or input_name == "email":
            return "email"
    for kw in _PHONE_KWS:
        if kw in lower or kw in input_name:
            return "phone"
    for kw in _CONTACT_KWS:
        if kw in lower or kw in input_name:
            return "contact_method"
    for kw in _NAME_KWS:
        if kw in lower or kw in input_name:
            return "name"
    for kw in _MESSAGE_KWS:
        if kw in lower or kw in input_name:
            return "message"

    if input_type == "submit":
        return "ignore"
    return "unknown"


class FormExtractionStrategy(ParsingStrategy):
    @property
    def name(self) -> str:
        return "form_extraction"

    @property
    def weight(self) -> float:
        return 0.15

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult:
        result = ParsedResult()
        for form in soup.find_all("form"):
            if _is_login_form(form):
                continue
            self._process_form(form, result, url)
        return result

    def parse_segments(self, segments: list[Any], url: str) -> ParsedResult:
        result = ParsedResult()
        for seg in segments:
            if isinstance(seg, Tag):
                for form in seg.find_all("form"):
                    if _is_login_form(form):
                        continue
                    self._process_form(form, result, url)
            else:
                sub = (
                    seg.to_soup()
                    if hasattr(seg, "to_soup")
                    else BeautifulSoup(str(seg), "lxml")
                )
                for form in sub.find_all("form"):
                    if _is_login_form(form):
                        continue
                    self._process_form(form, result, url)
        return result

    def _process_form(self, form: Tag, result: ParsedResult, url: str) -> None:
        seen_emails: set[str] = set()
        seen_phones: set[str] = set()
        seen_categories: set[str] = set()
        seen_cities: set[str] = set()
        seen_contact_methods: set[str] = set()

        for inp in form.find_all(["input", "select", "textarea"]):
            if not isinstance(inp, Tag):
                continue
            if inp.name == "input":
                input_type = str(inp.get("type", "") or "").lower()
                if input_type in ("hidden", "submit", "button", "reset", "image", "file"):
                    continue

            label = _get_label_text(inp, form)
            field_type = _classify_field(label, inp)

            if field_type == "ignore":
                continue

            if field_type == "email":
                val = self._input_value(inp)
                _maybe_extract_email(val, seen_emails, result)

            elif field_type == "phone":
                val = self._input_value(inp)
                if val and result.contact_phone is None:
                    clean = re.sub(r"[^\d+\-()\s.ext]", "", val).strip()
                    if clean and len(clean) >= 7:
                        result.contact_phone = clean
                        seen_phones.add(clean)

            elif field_type == "category":
                if inp.name == "select":
                    for opt in _collect_select_options(inp):
                        if opt.lower() not in ("select", "choose", ""):
                            seen_categories.add(opt)
                else:
                    val = self._input_value(inp)
                    if val:
                        seen_categories.add(val)

            elif field_type == "city":
                if inp.name == "select":
                    for opt in _collect_select_options(inp):
                        if opt.lower() not in ("select", "choose", ""):
                            seen_cities.add(opt)
                else:
                    val = self._input_value(inp)
                    _maybe_extract_email(val, seen_emails, result)
                    if val and not _EMAIL_RE.search(val):
                        seen_cities.add(val)

            elif field_type == "contact_method":
                if inp.name == "select":
                    for opt in _collect_select_options(inp):
                        seen_contact_methods.add(opt)
                elif inp.name == "input" and inp.get("type") in ("radio", "checkbox"):
                    for opt in _collect_radio_checkbox_options(
                        inp.find_parent(["form", "fieldset", "div"]) or form
                    ):
                        seen_contact_methods.add(opt)
                else:
                    val = self._input_value(inp)
                    if val:
                        seen_contact_methods.add(val)

            elif field_type == "name" or field_type == "message":
                pass

            elif field_type == "unknown":
                val = self._input_value(inp)
                _maybe_extract_email(val, seen_emails, result)
                if inp.name == "select":
                    for opt in _collect_select_options(inp):
                        seen_categories.add(opt)

        self._emit_results(result, seen_categories, seen_cities, seen_contact_methods)

    def _input_value(self, inp: Tag) -> str | None:
        if inp.name == "select":
            selected = inp.find("option", attrs={"selected": True})
            if selected:
                return selected.get_text(strip=True) or str(selected.get("value", "") or "")
            first = inp.find("option")
            if first:
                return first.get_text(strip=True) or str(first.get("value", "") or "")
            return None
        val = inp.get("value")
        if val and isinstance(val, str) and val.strip():
            return val.strip()
        placeholder = inp.get("placeholder")
        if placeholder and isinstance(placeholder, str) and placeholder.strip():
            return placeholder.strip()
        return None

    def _emit_results(
        self,
        result: ParsedResult,
        categories: set[str],
        cities: set[str],
        contact_methods: set[str],
    ) -> None:
        for cat in categories:
            if not cat or len(cat) < 2:
                continue
            exists = any(s.get("category") == cat and s.get("name") == cat for s in result.services)
            if not exists:
                result.services.append(
                    {
                        "name": cat,
                        "description": None,
                        "category": cat,
                        "starting_price": None,
                        "currency": "USD",
                        "estimated_duration": None,
                        "source": "form_category",
                    }
                )

        for city in cities:
            if not city or len(city) < 2:
                continue
            exists = any(
                s.get("name") == city and s.get("source") == "form_city" for s in result.services
            )
            if not exists:
                result.services.append(
                    {
                        "name": city,
                        "description": None,
                        "category": "Location",
                        "starting_price": None,
                        "currency": "USD",
                        "estimated_duration": None,
                        "source": "form_city",
                    }
                )

        for method in contact_methods:
            if not method or len(method) < 2:
                continue
            exists = any(
                c.get("title") == method and c.get("content_type") == "contact_method"
                for c in result.content
            )
            if not exists:
                result.content.append(
                    {
                        "title": method,
                        "author": None,
                        "publish_date": None,
                        "url": "",
                        "summary": None,
                        "content_type": "contact_method",
                    }
                )


def _maybe_extract_email(text: str | None, seen: set[str], result: ParsedResult) -> None:
    if not text:
        return
    for match in _EMAIL_RE.finditer(text):
        email = match.group(0)
        if email not in seen and not email.endswith(
            (".png", ".jpg", ".gif", ".svg", ".css", ".js")
        ):
            seen.add(email)
            if result.contact_email is None:
                result.contact_email = email
