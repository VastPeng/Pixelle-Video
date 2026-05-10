# Copyright (C) 2025 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Topic selector component with [topic] content format
"""

import re
from typing import Optional

import streamlit as st

from web.i18n import tr
from web.utils.streamlit_helpers import safe_rerun


def parse_topic_content(text: str) -> tuple[Optional[str], str]:
    """Parse [topic] content format"""
    match = re.match(r'\[([^\]]+)\]\s*(.*)', text, re.DOTALL)
    if match:
        return match.group(1), match.group(2)
    return None, text


def format_topic_content(topic: Optional[str], content: str) -> str:
    """Format topic and content into [topic] content format"""
    if topic:
        return f"[{topic}] {content}"
    return content


def render_topic_input(
    label: str = "",
    placeholder: str = "",
    height: int = 150,
    key: str = "topic_input",
) -> tuple[Optional[str], str]:
    """Render topic input with / trigger support"""
    if not label:
        label = tr("topic.input_label")
    if not placeholder:
        placeholder = tr("topic.input_placeholder")

    text = st.text_area(
        label,
        value=st.session_state.get(key, ""),
        placeholder=placeholder,
        height=height,
        key=key,
    )

    topic, content = parse_topic_content(text)

    if text.endswith("/"):
        available_topics = st.session_state.get("available_topics", [
            tr("topic.ai"), tr("topic.tech_product"), tr("topic.tutorial"),
            tr("topic.news"), tr("topic.marketing"), tr("topic.brand_story"),
            tr("topic.product_launch"), tr("topic.industry_analysis"),
        ])
        selected = st.selectbox(
            tr("topic.select_topic"),
            options=available_topics,
            key=f"{key}_selector",
        )
        if st.button(tr("topic.confirm"), key=f"{key}_confirm"):
            current_content = content if content else ""
            st.session_state[key] = f"[{selected}] {current_content}"
            safe_rerun()

    return topic, content
