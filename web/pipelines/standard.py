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
Standard Pipeline UI

Implements the 2-column layout per design spec section 六:
- Left column: Content input + Style config
- Right column: Post-processing config + Output preview
- Below: External services config
"""

import streamlit as st
from typing import Any
from web.i18n import tr

from web.pipelines.base import PipelineUI, register_pipeline_ui

# Import components
from web.components.content_input import render_content_input, render_bgm_section, render_version_info
from web.components.style_config import render_style_config
from web.components.output_preview import render_output_preview
from web.components.post_processing_config import render_post_processing_config
from web.components.external_services_config import render_external_services_config


class StandardPipelineUI(PipelineUI):
    """
    UI for the Standard Video Generation Pipeline.
    Implements the 2-column layout per design spec.
    """
    name = "quick_create"
    icon = "⚡"

    @property
    def display_name(self):
        return tr("pipeline.quick_create.name")

    @property
    def description(self):
        return tr("pipeline.quick_create.description")

    def render(self, pixelle_video: Any):
        # Two-column layout (per design spec)
        left_col, right_col = st.columns([1, 1])

        # ====================================================================
        # Left Column: Content Input + Style Config
        # ====================================================================
        with left_col:
            # Content input (mode, text, title, n_scenes)
            content_params = render_content_input()

            # Style configuration (TTS, template, workflow, etc.)
            style_params = render_style_config(pixelle_video)

            # BGM selection (bgm_path, bgm_volume)
            bgm_params = render_bgm_section()

            # Version info & GitHub link
            render_version_info()

        # ====================================================================
        # Right Column: Post-processing + Output Preview
        # ====================================================================
        with right_col:
            # Post-processing configuration (Coze plugin, toolchain)
            render_post_processing_config()

            # Combine all parameters
            video_params = {
                "pipeline": self.name,
                **content_params,
                **bgm_params,
                **style_params
            }

            # Render output preview (generate button, progress, video preview)
            render_output_preview(pixelle_video, video_params)

        # ====================================================================
        # Below Columns: External Services Config
        # ====================================================================
        st.divider()
        render_external_services_config()


# Register self
register_pipeline_ui(StandardPipelineUI)
