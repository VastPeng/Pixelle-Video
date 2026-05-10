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
External services configuration UI component
"""

import streamlit as st

from web.i18n import tr
from web.utils.streamlit_helpers import safe_rerun


def render_external_services_config():
    """Render external services configuration panel"""
    with st.container(border=True):
        st.markdown(f"**{tr('section.external_services')}**")

        with st.expander(tr("help.feature_description"), expanded=False):
            st.markdown(f"**{tr('help.what')}**")
            st.markdown(tr("external_services.what"))
            st.markdown(f"**{tr('help.how')}**")
            st.markdown(tr("external_services.how"))

        stages = {
            tr("external_services.stage.input"): "input",
            tr("external_services.stage.processing"): "processing",
            tr("external_services.stage.output"): "output",
        }
        tabs = st.tabs(list(stages.keys()))

        for i, (stage_label, stage_value) in enumerate(stages.items()):
            with tabs[i]:
                services = st.session_state.get(f"ext_services_{stage_value}", [])

                # Iterate in reverse to safely delete during iteration
                for j in range(len(services) - 1, -1, -1):
                    service = services[j]
                    with st.container():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.write(f"**{service['name']}**")
                            st.caption(f"URL: {service['url']}")
                        with col2:
                            st.button(
                                tr("external_services.configure"),
                                key=f"ext_cfg_{stage_value}_{j}",
                                disabled=True,
                            )
                        with col3:
                            if st.button(
                                tr("external_services.delete"),
                                key=f"ext_del_{stage_value}_{j}",
                            ):
                                services.pop(j)
                                st.session_state[f"ext_services_{stage_value}"] = services
                                safe_rerun()

                with st.expander(f"+ {tr('external_services.add_service')}"):
                    new_name = st.text_input(
                        tr("external_services.service_name"),
                        key=f"new_name_{stage_value}",
                    )
                    new_url = st.text_input(
                        tr("external_services.service_url"),
                        key=f"new_url_{stage_value}",
                    )
                    new_method = st.selectbox(
                        tr("external_services.request_method"),
                        ["GET", "POST"],
                        key=f"new_method_{stage_value}",
                    )
                    new_auth_type = st.selectbox(
                        tr("external_services.auth_type"),
                        ["none", "bearer", "api_key"],
                        key=f"new_auth_{stage_value}",
                    )
                    new_token = ""
                    if new_auth_type != "none":
                        new_token = st.text_input(
                            "Token/Key",
                            type="password",
                            key=f"new_token_{stage_value}",
                        )

                    if st.button(
                        tr("external_services.add"),
                        key=f"add_service_{stage_value}",
                    ):
                        if new_name and new_url:
                            services.append({
                                "name": new_name,
                                "url": new_url,
                                "method": new_method,
                                "auth_type": new_auth_type,
                                "token": new_token,
                            })
                            st.session_state[f"ext_services_{stage_value}"] = services
                            st.success(tr("external_services.added", name=new_name))
