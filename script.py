class script(object):

    START_TXT = """<b>Hey, {}!</b>

<b>I am a Web Novel Scraper Bot 📚</b>
<b>Send me a novel link or type /search to find novels.</b>
"""

    HELP_TXT = """<b>

Send novel link → I fetch chapters
/search name → I find novels
Download → TXT / PDF / EPUB

Supports large novels with thousands of chapters.
</b>"""

    ABOUT_TXT = """<b>

Bot Name : Zero Novel Scraper
Developer : <a href="https://t.me/Venuboyy">ZeroDev</a>
Library : Pyrogram
Language : Python 3
Database : MongoDB
</b>"""

    FORCE_SUB_TXT = """<b>⚠️ Access Denied!</b>

You must join both channels below to use this bot.

After joining, tap <b>✅ I Joined</b> to continue."""

    INFO_TXT = """<b>👤 User Information</b>

<b>First Name :</b> {first}
<b>Last Name  :</b> {last}
<b>Username   :</b> @{uname}
<b>User ID    :</b> <code>{uid}</code>
<b>DC ID      :</b> {dc}"""

    SETTINGS_TXT = """<b>⚙️ Settings</b>

Configure your reading preferences below."""

    STATS_TXT = """<b>📊 Bot Statistics</b>

<b>Total Users    :</b> {users}
<b>Active Today   :</b> {active}
<b>Novels Scraped :</b> {novels}
<b>Chapters Sent  :</b> {chapters}"""

    CHAPTER_TXT = """<b>📖 {title}</b>
<b>Chapter {num}: {chap_title}</b>
━━━━━━━━━━━━━━━━━━━━━
{content}
━━━━━━━━━━━━━━━━━━━━━
<i>📚 Zero Novel Scraper | @zerodev2</i>"""

    DOWNLOAD_PROGRESS = """<b>📚 Fetching Chapters...</b>

{bar}

<b>📥 Chapters Collected :</b> {done}/{total}
<b>⚡ Progress           :</b> {pct}%
<b>⏳ Est. Time Left    :</b> {eta}"""
