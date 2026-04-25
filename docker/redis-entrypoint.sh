#!/bin/sh
# Copyright 2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


set -e

# Generate the Redis ACL file from environment variables at container startup.
# Writes to /tmp/users.acl, referenced via --aclfile in the server command.
# Passwords must not contain newlines or null bytes.
cat > /tmp/users.acl <<EOF
user bot on >${BOT_REDIS_PASSWORD} %RW~proj:* %RW~bot:* %RW~discord:guild:* %RW~discord:guild_channels:* %RW~discord:channel:* %RW~discord:guild_roles:* %RW~discord:global_rate_limit %RW~channel_rate_limit:* %RW~api:user_roles:* +@all -@admin -@dangerous +scan +del
user api on >${API_REDIS_PASSWORD} %R~proj:* %R~bot:* %R~discord:guild:* %R~discord:guild_channels:* %R~discord:channel:* %R~discord:guild_roles:* %RW~discord:global_rate_limit %RW~channel_rate_limit:* %RW~api:* +@all -@admin -@dangerous +scan
user test on >${TEST_REDIS_PASSWORD} ~* &* +@all -@admin
user default on nopass nocommands +ping
EOF

exec docker-entrypoint.sh "$@"
