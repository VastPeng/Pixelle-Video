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
Post-processing configuration UI component
"""

import streamlit as st

from web.i18n import tr


def render_post_processing_config():
    """Render post-processing configuration panel"""
    with st.container(border=True):
        st.markdown(f"**{tr('section.post_processing')}**")

        with st.expander(tr("help.feature_description"), expanded=False):
            st.markdown(f"**{tr('help.what')}**")
            st.markdown(tr("post_processing.what"))
            st.markdown(f"**{tr('help.how')}**")
            st.markdown(tr("post_processing.how"))

        coze_enabled = st.toggle(
            tr("post_processing.coze_enabled"),
            value=st.session_state.get("coze_enabled", False),
            help=tr("post_processing.coze_enabled_help"),
        )
        st.session_state["coze_enabled"] = coze_enabled

        if not coze_enabled:
            return

        presets = {
            "product_video": tr("post_processing.preset.product_video"),
            "tutorial_video": tr("post_processing.preset.tutorial_video"),
            "marketing_video": tr("post_processing.preset.marketing_video"),
            "news_video": tr("post_processing.preset.news_video"),
            "standard": tr("post_processing.preset.standard"),
        }

        preset_name = st.selectbox(
            tr("post_processing.video_type"),
            options=list(presets.keys()),
            format_func=lambda x: presets[x],
            key="post_preset_select",
        )
        st.session_state["post_preset"] = preset_name

        smart_decision = st.toggle(
            tr("post_processing.smart_decision"),
            value=True,
            help=tr("post_processing.smart_decision_help"),
        )
        st.session_state["smart_decision"] = smart_decision

        default_tools_map = {
            "product_video": ["add_subtitles", "video_super_resolution"],
            "tutorial_video": ["add_subtitles", "audio_denoise"],
            "marketing_video": ["concat_videos", "add_text", "video_hdr"],
            "news_video": ["add_subtitles", "video_speed"],
            "standard": ["add_subtitles"],
        }

        default_tools = default_tools_map.get(preset_name, ["add_subtitles"])
        all_tools = [
            "add_subtitles", "video_super_resolution", "concat_videos",
            "audio_denoise", "video_speed", "video_hdr", "insert_frame",
            "audio_to_subtitle", "add_text", "compile_video_audio",
        ]

        st.write(f"**{tr('post_processing.toolchain_preview')}:**")
        selected_tools = []
        tool_col1, tool_col2 = st.columns(2)
        for i, tool in enumerate(all_tools):
            default_checked = tool in default_tools
            col = tool_col1 if i < len(all_tools) // 2 + 1 else tool_col2
            with col:
                enabled = st.checkbox(
                    tool,
                    value=default_checked,
                    key=f"pp_tool_{tool}",
                )
                if enabled:
                    selected_tools.append(tool)

        st.session_state["selected_pp_tools"] = selected_tools

        output_resolution = st.selectbox(
            tr("post_processing.output_resolution"),
            options=["720P", "1080P", "2K", "4K"],
            index=1,
            key="pp_output_resolution",
        )
        st.session_state["pp_output_resolution"] = output_resolution
