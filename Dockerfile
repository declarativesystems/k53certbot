# Copyright 2020 Declarative Systems Pty Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM python:3.8.6-buster
ARG K53CERTBOT_VERSION
COPY dist/k53certbot-${K53CERTBOT_VERSION}-py3-none-any.whl /tmp/k53certbot-${K53CERTBOT_VERSION}-py3-none-any.whl
RUN pip install /tmp/k53certbot-${K53CERTBOT_VERSION}-py3-none-any.whl


ENTRYPOINT k53certbot
