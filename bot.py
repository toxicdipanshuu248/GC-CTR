"""
𝐉ᴏʜɴ 𝐖ɪᴄᴋ.་༘࿐ ᯓ 𝐌⃝ᴀнσɾαgᴀ ⋆ཋྀ🪽𓆪  —  Telegram GC Controller Bot
Controller : Normal Bot (Bot API) with inline keyboard UI
Engine     : Logged-in user account (phone -> OTP -> 2FA)
Hosting    : Render web service + UptimeRobot ping (keep-alive HTTP server included)
"""
import asyncio, json, os, re, logging
from aiohttp import web
from pyrogram import Client, filters, idle
from pyrogram.types import (ChatPrivileges, Message, InlineKeyboardMarkup as IKM,
                            InlineKeyboardButton as IKB, CallbackQuery)
from pyrogram.errors import (SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired,
                             PasswordHashInvalid, FloodWait, UserPrivacyRestricted,
                             UserNotMutualContact)
from pyrogram.raw import functions, types as rt

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("aura")

# ══════════════════════════ CONFIG (hardcoded) ══════════════════════════
API_ID    = 35404440
API_HASH  = "b60a96d88f23a5ffb2fb4556d7c00ed7"
BOT_TOKEN = "8475642506:AAFOhHElT9qJ93o3WPI0yLPPPOMCRAOWVwQ"
OWNER_ID  = 5206554804

BRAND       = "𝐉ᴏʜɴ 𝐖ɪᴄᴋ.་༘࿐ ᯓ 𝐌⃝ᴀнσɾαgᴀ ⋆ཋྀ🪽𓆪"
FOLDER_NAME = "AURA X DEV"
GC_NAME     = "DEV BHAGWAN"
GC_DESC     = "CREATED BY GO4T DEV"
PORT        = int(os.getenv("PORT", "8080"))       # Render injects PORT
DATA_DIR    = os.getenv("DATA_DIR", "data")        # mount a Render disk here for persistence
# ════════════════════════════════════════════════════════════════════════

os.makedirs(DATA_DIR, exist_ok=True)
SESS_FILE = os.path.join(DATA_DIR, "sessions.json")
GC_FILE   = os.path.join(DATA_DIR, "groups.json")
SUDO_FILE = os.path.join(DATA_DIR, "sudo.json")

def _load(path, default):
    try: return json.load(open(path))
    except Exception: return default
def _save(path, obj): json.dump(obj, open(path, "w"))

def get_session(uid):      return _load(SESS_FILE, {}).get(str(uid))
def set_session(uid, s):   d = _load(SESS_FILE, {}); d[str(uid)] = s; _save(SESS_FILE, d)
def del_session(uid):      d = _load(SESS_FILE, {}); d.pop(str(uid), None); _save(SESS_FILE, d)
def load_groups(uid):      return _load(GC_FILE, {}).get(str(uid), [])
def save_groups(uid, ids): d = _load(GC_FILE, {}); d[str(uid)] = ids; _save(GC_FILE, d)
def load_sudo():           return set(_load(SUDO_FILE, []))
def save_sudo(ids):        _save(SUDO_FILE, sorted(ids))
def allowed_ids():         return {OWNER_ID} | load_sudo()

bot = Client("controller", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

state        = {}   # uid -> wizard dict
user_clients = {}   # uid -> Client
cmd_mode     = {}   # uid -> broadcast config
scope_pref   = {}   # uid -> "made" | "all"

FULL_ADMIN = ChatPrivileges(
    can_manage_chat=True, can_delete_messages=True, can_manage_video_chats=True,
    can_restrict_members=True, can_promote_members=True, can_change_info=True,
    can_invite_users=True, can_pin_messages=True, can_post_messages=True,
    can_edit_messages=True, is_anonymous=False)

def H(title: str) -> str:
    return f"**{BRAND}**\n〰️〰️〰️〰️〰️〰️〰️〰️\n**{title}**\n\n"

async def get_user_client(uid):
    if uid in user_clients: return user_clients[uid]
    s = get_session(uid)
    if not s: return None
    c = Client(f"u{uid}", api_id=API_ID, api_hash=API_HASH, session_string=s, in_memory=True)
    try:
        await c.start()
    except Exception as e:
        log.warning(f"session {uid} dead: {e}"); del_session(uid); return None
    user_clients[uid] = c
    return c

# ══════════════════════════ ACCESS CONTROL ══════════════════════════
allowed    = filters.create(lambda _, __, m: bool(m.from_user) and m.from_user.id in allowed_ids())
main_owner = filters.create(lambda _, __, m: bool(m.from_user) and m.from_user.id == OWNER_ID)

@bot.on_message(filters.private & ~allowed, group=-1)
async def deny_msg(_, m: Message):
    await m.reply(H("🚫 Access Denied") +
                  f"This is a private controller bot.\nYour ID: `{m.from_user.id}`\n"
                  f"Ask the owner to run `.auth {m.from_user.id}`")
    m.stop_propagation()

@bot.on_callback_query(~allowed, group=-1)
async def deny_cb(_, q: CallbackQuery):
    await q.answer("🚫 Access denied", show_alert=True); q.stop_propagation()

# ══════════════════════════ KEYBOARDS ══════════════════════════
def kb_main(logged: bool):
    return IKM([
        [IKB("🚪 Logout" if logged else "🔐 Login", "logout" if logged else "login"),
         IKB("📊 Status", "status")],
        [IKB("🏗 GC Maker", "gc"), IKB("🛠 Manage GC", "manage")],
        [IKB("📢 Broadcast", "bc"), IKB("📂 Folders", "folders")],
        [IKB("👑 Access", "access"), IKB("📖 Help", "help")],
    ])

def kb_manage():
    return IKM([
        [IKB("👢 Kick users", "mg_kick"), IKB("🤖 Kick all bots", "mg_kickbots")],
        [IKB("➕ Add users", "mg_add"), IKB("⭐ Promote", "mg_promote")],
        [IKB("⬇️ Demote", "mg_demote"), IKB("✏️ Rename", "mg_rename")],
        [IKB("📝 Description", "mg_desc"), IKB("🖼 Set photo", "mg_setpic")],
        [IKB("🔗 Links", "mg_link"), IKB("📋 List", "mg_list")],
        [IKB("🚪 Leave all", "mg_leave"), IKB("🗑 Delete all", "mg_delete")],
        [IKB("🎯 Scope", "mg_scope"), IKB("🏠 Menu", "menu")],
    ])

def kb_scope(cur):
    return IKM([[IKB(("✅ " if cur == "made" else "") + "Bot-made GCs", "scope_made"),
                 IKB(("✅ " if cur == "all" else "") + "All owned groups", "scope_all")],
                [IKB("⬅️ Back", "manage")]])

def kb_bc(cm):
    on = cm.get("on")
    return IKM([
        [IKB("🟢 ON: Bot-made GCs", "bc_on_made"), IKB("🟢 ON: All groups", "bc_on_all")],
        [IKB("📂 ON: Pick a folder", "bc_on_folder")],
        [IKB(("✅ " if cm.get("mode", "copy") == "copy" else "") + "Copy mode", "bc_mode_copy"),
         IKB(("✅ " if cm.get("mode") == "forward" else "") + "Forward mode", "bc_mode_forward")],
        [IKB("🔴 Turn OFF", "bc_off") if on else IKB("ℹ️ Status", "bc_status"), IKB("🏠 Menu", "menu")],
    ])

def kb_back(cb="menu"): return IKM([[IKB("⬅️ Back", cb)]])
def kb_cancel():        return IKM([[IKB("❌ Cancel", "cancel")]])
def kb_confirm(action): return IKM([[IKB("✅ Yes, do it", f"confirm_{action}"), IKB("❌ No", "manage")]])
def kb_access():        return IKM([[IKB("➕ Allow user", "acc_add"), IKB("➖ Remove user", "acc_del")],
                                    [IKB("📋 List", "acc_list"), IKB("🏠 Menu", "menu")]])

HELP_TEXT = H("📖 Command Reference") + f"""**Account**
/login · /logout · /status · /menu

**GC Maker**  `/gc` → folder? → count → members
Name `{GC_NAME}` · Desc `{GC_DESC}` · Folder `{FOLDER_NAME}`

**Manage (applies to ALL target GCs)**
`.kick @a @b` · `.kickbots` · `.add @a @b`
`.promote @a @b` · `.demote @a @b`
`.rename <name>` · `.desc <text>` · `.setpic` (reply to a photo)
`.link` · `.list` · `.leave` · `.delete confirm` · `.scope made|all`

**Broadcast**
`.folders` · `.cmd on` · `.cmd on <folder>` · `.cmd on all`
`.cmd mode copy|forward` · `.cmd off` · `.cmd status`
While ON, every message you send here is relayed to all target GCs.

**Owner only**
`.auth <id>` · `.unauth <id>` · `.authlist`
"""

# ══════════════════════════ MENU / BASIC ══════════════════════════
async def render_menu(uid):
    c = await get_user_client(uid)
    name = "not logged in"
    if c:
        try: me = await c.get_me(); name = f"{me.first_name} (`{me.phone_number}`)"
        except Exception: pass
    txt = H("🏠 Main Menu") + f"👤 Account: {name}\n📦 Tracked GCs: `{len(load_groups(uid))}`\n\nChoose an option below."
    return txt, kb_main(bool(c))

@bot.on_message(filters.command(["start", "menu"]) & filters.private & allowed)
async def start_cmd(_, m: Message):
    t, k = await render_menu(m.from_user.id); await m.reply(t, reply_markup=k)

@bot.on_message(filters.command("help") & filters.private & allowed)
async def help_cmd(_, m: Message): await m.reply(HELP_TEXT, reply_markup=kb_back())

async def status_text(uid):
    c = await get_user_client(uid)
    if not c: return H("📊 Status") + "❌ Not logged in. Press **Login**."
    me = await c.get_me()
    cm = cmd_mode.get(uid, {})
    return (H("📊 Status") + f"✅ Logged in as **{me.first_name}** (`{me.phone_number}`)\n"
            f"📦 Tracked GCs: `{len(load_groups(uid))}`\n🎯 Scope: `{scope_pref.get(uid, 'made')}`\n"
            f"📢 Broadcast: {'🟢 ON → ' + cm.get('label', '') if cm.get('on') else '🔴 OFF'}")

@bot.on_message(filters.command("status") & filters.private & allowed)
async def status_cmd(_, m: Message): await m.reply(await status_text(m.from_user.id), reply_markup=kb_back())

async def do_cancel(uid):
    st = state.pop(uid, None)
    if st and st.get("client"):
        try: await st["client"].disconnect()
        except Exception: pass

@bot.on_message(filters.command("cancel") & filters.private & allowed)
async def cancel_cmd(_, m: Message):
    await do_cancel(m.from_user.id); await m.reply("✅ Cancelled.", reply_markup=kb_back())

async def do_logout(uid):
    c = user_clients.pop(uid, None)
    if c:
        try: await c.log_out()
        except Exception: pass
    del_session(uid)

@bot.on_message(filters.command("logout") & filters.private & allowed)
async def logout_cmd(_, m: Message):
    await do_logout(m.from_user.id); await m.reply("✅ Logged out.", reply_markup=kb_back())

# ══════════════════════════ LOGIN ══════════════════════════
async def begin_login(m: Message, uid):
    if await get_user_client(uid):
        return await m.reply("✅ Already logged in. Logout first to switch accounts.", reply_markup=kb_back())
    state[uid] = {"step": "phone"}
    await m.reply(H("🔐 Login") + "Send your phone number with country code.\nExample: `+919876543210`",
                  reply_markup=kb_cancel())

@bot.on_message(filters.command("login") & filters.private & allowed)
async def login_cmd(_, m: Message): await begin_login(m, m.from_user.id)

async def finish_login(m, uid, c):
    set_session(uid, await c.export_session_string())
    me = await c.get_me()
    user_clients[uid] = c
    state.pop(uid, None)
    t, k = await render_menu(uid)
    await m.reply(H("✅ Login Successful") + f"Welcome, **{me.first_name}**!\n\n" + t.split("\n\n", 1)[1], reply_markup=k)

# ══════════════════════════ GC WIZARD ══════════════════════════
async def begin_gc(m: Message, uid):
    if not await get_user_client(uid):
        return await m.reply("❌ Please login first.", reply_markup=kb_main(False))
    state[uid] = {"step": "folder_q"}
    await m.reply(H("🏗 GC Maker · Step 1/3") +
                  f"Create a new folder **{FOLDER_NAME}** and put all groups inside it?",
                  reply_markup=IKM([[IKB("📂 Folder", "gcw_folder"), IKB("📄 Normal", "gcw_normal")],
                                    [IKB("❌ Cancel", "cancel")]]))

@bot.on_message(filters.command("gc") & filters.private & allowed)
async def gc_cmd(_, m: Message): await begin_gc(m, m.from_user.id)

async def gc_ask_count(m, uid, use_folder):
    state[uid] = {"step": "count", "folder": use_folder}
    await m.reply(H("🏗 GC Maker · Step 2/3") + "How many groups should I create? (1–50)",
                  reply_markup=IKM([[IKB("5", "gcn_5"), IKB("10", "gcn_10"), IKB("15", "gcn_15"), IKB("20", "gcn_20")],
                                    [IKB("❌ Cancel", "cancel")]]))

async def gc_ask_members(m, uid, count):
    state[uid].update({"step": "members", "count": count})
    await m.reply(H("🏗 GC Maker · Step 3/3") +
                  "Send the usernames to add & promote as **full admin** (users and bots), e.g.\n"
                  "`@user1 @somebot @user2`",
                  reply_markup=IKM([[IKB("⏭ Skip (no members)", "gcm_skip")], [IKB("❌ Cancel", "cancel")]]))

async def run_gc_job(m: Message, uid: int, st: dict):
    c = await get_user_client(uid)
    count, members, use_folder = st["count"], st["members"], st["folder"]
    prog = await m.reply(H("🚀 Working") + f"Creating {count} groups…")
    resolved = []
    for u in members:
        try: resolved.append(await c.get_users(u))
        except Exception: await m.reply(f"⚠️ `@{u}` not found, skipped.")
    created, lines = [], []
    for i in range(1, count + 1):
        try:
            chat = await c.create_supergroup(GC_NAME, GC_DESC)
        except FloodWait as e:
            await prog.edit(H("⏳ FloodWait") + f"Waiting {e.value}s… ({i}/{count})")
            await asyncio.sleep(e.value + 1)
            try: chat = await c.create_supergroup(GC_NAME, GC_DESC)
            except Exception as e2: lines.append(f"❌ GC {i}: `{e2}`"); continue
        except Exception as e:
            lines.append(f"❌ GC {i}: `{e}`"); continue
        created.append(chat)
        line = f"✅ GC {i}"
        for usr in resolved:
            tag = f"@{usr.username}" if usr.username else usr.id
            try: await c.add_chat_members(chat.id, usr.id)
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
                try: await c.add_chat_members(chat.id, usr.id)
                except Exception: pass
            except (UserPrivacyRestricted, UserNotMutualContact): lines.append(f"  ⚠️ {tag}: privacy restricted")
            except Exception as e: lines.append(f"  ⚠️ {tag}: add failed `{type(e).__name__}`")
            try: await c.promote_chat_member(chat.id, usr.id, FULL_ADMIN)
            except Exception as e: lines.append(f"  ⚠️ {tag}: promote failed `{type(e).__name__}`")
        try: line += f" — {await c.export_chat_invite_link(chat.id)}"
        except Exception: pass
        lines.append(line)
        try: await prog.edit(H("⚙️ Working") + f"{i}/{count} groups done…")
        except Exception: pass
        await asyncio.sleep(2)
    ids = load_groups(uid); ids += [ch.id for ch in created if ch.id not in ids]; save_groups(uid, ids)
    if use_folder and created:
        try: await make_folder(c, created); lines.append(f"📂 {len(created)} groups added to folder **{FOLDER_NAME}**")
        except Exception as e: lines.append(f"⚠️ Folder error: `{e}`")
    try: await prog.delete()
    except Exception: pass
    out = H("🎉 GC Maker Report") + f"Created **{len(created)}/{count}** groups\n\n" + "\n".join(lines)
    for ch in [out[i:i+3800] for i in range(0, len(out), 3800)]:
        await m.reply(ch, disable_web_page_preview=True)
    await m.reply("Done ✅", reply_markup=kb_back())

async def make_folder(c: Client, chats):
    peers = [await c.resolve_peer(ch.id) for ch in chats]
    res = await c.invoke(functions.messages.GetDialogFilters())
    existing, used = None, set()
    for f in res.filters:
        if isinstance(f, rt.DialogFilter):
            used.add(f.id)
            if _ftitle(f) == FOLDER_NAME: existing = f
    if existing:
        fid, include, pinned, exclude = existing.id, list(existing.include_peers) + peers, existing.pinned_peers, existing.exclude_peers
    else:
        fid, include, pinned, exclude = 2, peers, [], []
        while fid in used: fid += 1
    try:
        flt = rt.DialogFilter(id=fid, title=rt.TextWithEntities(text=FOLDER_NAME, entities=[]),
                              pinned_peers=pinned, include_peers=include, exclude_peers=exclude)
        await c.invoke(functions.messages.UpdateDialogFilter(id=fid, filter=flt))
    except TypeError:
        flt = rt.DialogFilter(id=fid, title=FOLDER_NAME, pinned_peers=pinned, include_peers=include, exclude_peers=exclude)
        await c.invoke(functions.messages.UpdateDialogFilter(id=fid, filter=flt))

# ══════════════════════════ FOLDERS / BROADCAST ══════════════════════════
def _ftitle(f):
    t = getattr(f, "title", ""); return getattr(t, "text", t) or ""

async def get_folders(c: Client):
    res = await c.invoke(functions.messages.GetDialogFilters())
    out = {}
    for f in res.filters:
        if not hasattr(f, "include_peers"): continue
        ids = []
        for pr in list(f.include_peers) + list(getattr(f, "pinned_peers", [])):
            if isinstance(pr, rt.InputPeerChannel): ids.append(int(f"-100{pr.channel_id}"))
            elif isinstance(pr, rt.InputPeerChat): ids.append(-pr.chat_id)
        out[_ftitle(f)] = list(dict.fromkeys(ids))
    return out

async def all_groups(c: Client, owned_only=False):
    ids = []
    async for d in c.get_dialogs():
        ch = d.chat
        if ch.type.name in ("SUPERGROUP", "GROUP") and (not owned_only or getattr(ch, "is_creator", False)):
            ids.append(ch.id)
    return ids

async def folders_text(uid):
    c = await get_user_client(uid)
    if not c: return H("📂 Folders") + "❌ Please login first.", kb_back()
    fl = await get_folders(c)
    if not fl: return H("📂 Folders") + "No folders found.", kb_back()
    txt = H("📂 Folders") + "\n".join(f"• `{k}` — {len(v)} groups" for k, v in fl.items())
    return txt, kb_back()

def bc_cfg(uid): return cmd_mode.setdefault(uid, {"on": False, "targets": [], "label": "", "mode": "copy"})

def bc_text(uid):
    cm = bc_cfg(uid)
    return (H("📢 Broadcast System") +
            f"State: {'🟢 ON' if cm['on'] else '🔴 OFF'}\nTarget: `{cm['label'] or '-'}` ({len(cm['targets'])} GCs)\n"
            f"Mode: `{cm['mode']}`\n\nWhile ON, every message you send here (text/media/sticker) is relayed to all target GCs.")

async def bc_enable(uid, kind, folder=None):
    c = await get_user_client(uid)
    if not c: return "❌ Please login first."
    cm = bc_cfg(uid)
    if kind == "made": targets, label = load_groups(uid), "Bot-made GCs"
    elif kind == "all": targets, label = await all_groups(c), "All groups"
    else:
        fl = await get_folders(c)
        match = next((k for k in fl if k.lower() == folder.lower()), None)
        if not match: return "❌ Folder not found. Available: " + ", ".join(f"`{k}`" for k in fl)
        targets, label = fl[match], f"Folder: {match}"
    if not targets: return "❌ No groups in this target."
    cm.update({"on": True, "targets": targets, "label": label})
    return f"🟢 Broadcast ON → **{label}** ({len(targets)} GCs)"

@bot.on_message(allowed & filters.private & filters.regex(r"^\.folders(\s|$)"))
async def folders_cmd(_, m: Message):
    t, k = await folders_text(m.from_user.id); await m.reply(t, reply_markup=k)

@bot.on_message(allowed & filters.private & filters.regex(r"^\.cmd(\s|$)"))
async def cmd_system(_, m: Message):
    uid = m.from_user.id
    parts = m.text.split(maxsplit=2)
    sub = parts[1].lower() if len(parts) > 1 else ""
    arg = parts[2].strip() if len(parts) > 2 else ""
    cm = bc_cfg(uid)
    if sub == "off": cm["on"] = False; return await m.reply("🔴 Broadcast OFF.", reply_markup=kb_bc(cm))
    if sub == "mode" and arg in ("copy", "forward"):
        cm["mode"] = arg; return await m.reply(f"✅ Mode: **{arg}**", reply_markup=kb_bc(cm))
    if sub == "status": return await m.reply(bc_text(uid), reply_markup=kb_bc(cm))
    if sub == "on":
        r = await bc_enable(uid, "made" if not arg else "all" if arg.lower() == "all" else "folder", arg)
        return await m.reply(r, reply_markup=kb_bc(cm))
    await m.reply(bc_text(uid), reply_markup=kb_bc(cm))

def _bc_active(_, __, m):
    return (bool(m.from_user) and m.from_user.id not in state and cmd_mode.get(m.from_user.id, {}).get("on")
            and not (m.text or m.caption or "").startswith((".", "/")))

@bot.on_message(allowed & filters.private & filters.create(_bc_active), group=5)
async def broadcast_msg(_, m: Message):
    uid = m.from_user.id
    c = await get_user_client(uid)
    if not c: return
    cm = cmd_mode[uid]; targets = cm["targets"]
    prog = await m.reply(H("📢 Broadcasting") + f"0/{len(targets)}")
    ok, fail = 0, []
    for i, gid in enumerate(targets, 1):
        try:
            if cm["mode"] == "forward": await m.forward(gid)
            else: await send_copy(c, m, gid)
            ok += 1
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            try: await send_copy(c, m, gid); ok += 1
            except Exception as e2: fail.append(f"`{gid}`: {type(e2).__name__}")
        except Exception:
            try: await send_copy(c, m, gid); ok += 1
            except Exception as e2: fail.append(f"`{gid}`: {type(e2).__name__}")
        if i % 3 == 0:
            try: await prog.edit(H("📢 Broadcasting") + f"{i}/{len(targets)}")
            except Exception: pass
        await asyncio.sleep(1)
    txt = H("📢 Broadcast Report") + f"✅ Delivered to **{ok}/{len(targets)}** GCs"
    if fail: txt += "\n\n⚠️ Failed:\n" + "\n".join(fail[:30])
    await prog.edit(txt)

_dl_cache = {}
async def send_copy(c: Client, m: Message, gid: int):
    if m.text: return await c.send_message(gid, m.text, entities=m.entities, disable_web_page_preview=True)
    if m.sticker: return await c.send_sticker(gid, m.sticker.file_id)
    cap = m.caption or None
    path = _dl_cache.get(m.id) or await m.download(); _dl_cache[m.id] = path
    if m.photo:      return await c.send_photo(gid, path, caption=cap)
    if m.video:      return await c.send_video(gid, path, caption=cap)
    if m.animation:  return await c.send_animation(gid, path, caption=cap)
    if m.audio:      return await c.send_audio(gid, path, caption=cap)
    if m.voice:      return await c.send_voice(gid, path, caption=cap)
    if m.video_note: return await c.send_video_note(gid, path)
    if m.document:   return await c.send_document(gid, path, caption=cap)
    raise ValueError("unsupported message type")

# ══════════════════════════ MANAGE ══════════════════════════
async def target_groups(c, uid):
    return await all_groups(c, owned_only=True) if scope_pref.get(uid, "made") == "all" else load_groups(uid)

def parse_users(txt): return [u.lstrip("@") for u in re.split(r"[\s,]+", txt) if u.strip()]

async def for_each_group(m, ids, label, fn):
    prog = await m.reply(H(f"⚙️ {label}") + f"0/{len(ids)}")
    ok, lines = 0, []
    for i, gid in enumerate(ids, 1):
        try:
            r = await fn(gid); ok += 1
            if r: lines.append(r)
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            try:
                r = await fn(gid); ok += 1
                if r: lines.append(r)
            except Exception as e2: lines.append(f"⚠️ `{gid}`: {type(e2).__name__}")
        except Exception as e: lines.append(f"⚠️ `{gid}`: {type(e).__name__}")
        if i % 3 == 0:
            try: await prog.edit(H(f"⚙️ {label}") + f"{i}/{len(ids)}")
            except Exception: pass
    try: await prog.delete()
    except Exception: pass
    out = H(f"✅ {label}") + f"Completed on **{ok}/{len(ids)}** GCs\n" + "\n".join(lines)
    for ch in [out[i:i+3800] for i in range(0, len(out), 3800)]:
        await m.reply(ch, disable_web_page_preview=True)
    await m.reply("Done ✅", reply_markup=kb_back("manage"))

async def run_manage(m: Message, uid: int, cmd: str, arg: str):
    c = await get_user_client(uid)
    if not c: return await m.reply("❌ Please login first.", reply_markup=kb_main(False))
    if cmd == "scope":
        if arg not in ("all", "made"): return await m.reply("Usage: `.scope made` or `.scope all`")
        scope_pref[uid] = arg; return await m.reply(f"✅ Scope: **{arg}**", reply_markup=kb_manage())
    ids = await target_groups(c, uid)
    if not ids: return await m.reply("❌ No target GCs. Create some with GC Maker or switch scope to *all*.", reply_markup=kb_manage())

    if cmd == "list":
        lines = []
        for gid in ids:
            try: ch = await c.get_chat(gid); lines.append(f"• {ch.title} — `{gid}` ({ch.members_count} members)")
            except Exception as e: lines.append(f"• `{gid}` — ⚠️ {type(e).__name__}")
        return await m.reply(H("📋 Group List") + f"Total **{len(ids)}** GCs\n" + "\n".join(lines), reply_markup=kb_back("manage"))
    if cmd == "link":
        return await for_each_group(m, ids, "Invite Links", lambda gid: _link(c, gid))
    if cmd in ("kick", "add", "promote", "demote"):
        if not arg: return await m.reply(f"Usage: `.{cmd} @user1 @user2`")
        users = []
        for u in parse_users(arg):
            try: users.append(await c.get_users(u))
            except Exception: await m.reply(f"⚠️ `@{u}` not found, skipped.")
        if not users: return
        async def fn(gid):
            errs = []
            for usr in users:
                try:
                    if cmd == "kick": await c.ban_chat_member(gid, usr.id); await c.unban_chat_member(gid, usr.id)
                    elif cmd == "add": await c.add_chat_members(gid, usr.id)
                    elif cmd == "promote": await c.promote_chat_member(gid, usr.id, FULL_ADMIN)
                    else: await c.promote_chat_member(gid, usr.id, ChatPrivileges())
                except Exception as e: errs.append(f"@{usr.username or usr.id}: {type(e).__name__}")
            return f"⚠️ `{gid}`: " + ", ".join(errs) if errs else None
        return await for_each_group(m, ids, f"{cmd.title()} {len(users)} user(s)", fn)
    if cmd == "kickbots":
        me = await c.get_me()
        async def fn(gid):
            n = 0
            async for mem in c.get_chat_members(gid):
                if mem.user.is_bot and mem.user.id != me.id:
                    try: await c.ban_chat_member(gid, mem.user.id); await c.unban_chat_member(gid, mem.user.id); n += 1
                    except Exception: pass
            return f"• `{gid}`: {n} bot(s) kicked"
        return await for_each_group(m, ids, "Kick All Bots", fn)
    if cmd == "rename":
        if not arg: return await m.reply("Usage: `.rename New Name`")
        return await for_each_group(m, ids, "Rename", lambda gid: c.set_chat_title(gid, arg))
    if cmd == "desc":
        if not arg: return await m.reply("Usage: `.desc New description`")
        return await for_each_group(m, ids, "Description", lambda gid: c.set_chat_description(gid, arg))
    if cmd == "setpic":
        if not m.reply_to_message or not m.reply_to_message.photo:
            return await m.reply("Reply to a photo with `.setpic`.")
        path = await m.reply_to_message.download()
        await for_each_group(m, ids, "Set Photo", lambda gid: c.set_chat_photo(gid, photo=path))
        try: os.remove(path)
        except Exception: pass
        return
    if cmd == "leave":
        await for_each_group(m, ids, "Leave All", lambda gid: c.leave_chat(gid))
        if scope_pref.get(uid, "made") == "made": save_groups(uid, [])
        return
    if cmd == "delete":
        if arg.lower() != "confirm":
            return await m.reply(H("⚠️ Confirm Delete") + f"This will **permanently delete {len(ids)} GCs**.", reply_markup=kb_confirm("delete"))
        await for_each_group(m, ids, "Delete All", lambda gid: c.delete_supergroup(gid))
        if scope_pref.get(uid, "made") == "made": save_groups(uid, [])

async def _link(c, gid): return f"• {await c.export_chat_invite_link(gid)}"

@bot.on_message(allowed & filters.private & filters.regex(r"^\.(kick|kickbots|add|promote|demote|rename|desc|setpic|link|list|leave|delete|scope)(\s|$)"))
async def manage_handler(_, m: Message):
    parts = (m.text or m.caption or "").split(maxsplit=1)
    await run_manage(m, m.from_user.id, parts[0][1:].lower(), parts[1].strip() if len(parts) > 1 else "")

# ══════════════════════════ ACCESS (owner) ══════════════════════════
def access_text():
    return H("👑 Access Control") + f"Owner: `{OWNER_ID}`\nAllowed users:\n" + ("\n".join(f"• `{i}`" for i in sorted(load_sudo())) or "_none_")

@bot.on_message(main_owner & filters.private & filters.regex(r"^\.(auth|unauth|authlist)(\s|$)"))
async def auth_cmd(_, m: Message):
    parts = m.text.split(); cmd = parts[0][1:].lower()
    if cmd == "authlist": return await m.reply(access_text(), reply_markup=kb_access())
    ids = [int(x) for x in parts[1:] if x.lstrip("-").isdigit()]
    if m.reply_to_message and m.reply_to_message.forward_from: ids.append(m.reply_to_message.forward_from.id)
    if not ids: return await m.reply(f"Usage: `.{cmd} <user_id>`")
    sudo = load_sudo()
    if cmd == "auth": sudo |= set(ids)
    else: sudo -= set(i for i in ids if i != OWNER_ID)
    save_sudo(sudo)
    await m.reply(("✅ Allowed: " if cmd == "auth" else "✅ Removed: ") + ", ".join(f"`{i}`" for i in ids), reply_markup=kb_access())

@bot.on_message(filters.private & filters.regex(r"^\.(auth|unauth|authlist)(\s|$)") & allowed & ~main_owner)
async def auth_denied(_, m: Message): await m.reply("🚫 Owner only.")

# ══════════════════════════ CALLBACKS ══════════════════════════
@bot.on_callback_query(allowed)
async def callbacks(_, q: CallbackQuery):
    uid, d, m = q.from_user.id, q.data, q.message
    async def edit(t, k=None):
        try: await m.edit_text(t, reply_markup=k, disable_web_page_preview=True)
        except Exception: await m.reply(t, reply_markup=k, disable_web_page_preview=True)

    if d == "menu":    t, k = await render_menu(uid); await edit(t, k)
    elif d == "help":  await edit(HELP_TEXT, kb_back())
    elif d == "status": await edit(await status_text(uid), kb_back())
    elif d == "login":  await begin_login(m, uid)
    elif d == "logout": await do_logout(uid); t, k = await render_menu(uid); await edit(H("🚪 Logged out") + "Session removed.", k)
    elif d == "cancel": await do_cancel(uid); t, k = await render_menu(uid); await edit(t, k)
    elif d == "folders": t, k = await folders_text(uid); await edit(t, k)

    # GC wizard
    elif d == "gc": await begin_gc(m, uid)
    elif d in ("gcw_folder", "gcw_normal"):
        if state.get(uid, {}).get("step") != "folder_q": return await q.answer("Start GC Maker first", show_alert=True)
        await gc_ask_count(m, uid, d == "gcw_folder")
    elif d.startswith("gcn_"):
        if state.get(uid, {}).get("step") != "count": return await q.answer("Start GC Maker first", show_alert=True)
        await gc_ask_members(m, uid, int(d[4:]))
    elif d == "gcm_skip":
        st = state.get(uid)
        if not st or st.get("step") != "members": return await q.answer("Start GC Maker first", show_alert=True)
        st["members"] = []; state.pop(uid, None); await q.answer(); return await run_gc_job(m, uid, st)

    # manage
    elif d == "manage": await edit(H("🛠 Manage GCs") + f"Scope: `{scope_pref.get(uid, 'made')}` · Tracked: `{len(load_groups(uid))}`\nEvery action applies to ALL target GCs.", kb_manage())
    elif d == "mg_scope": await edit(H("🎯 Scope") + "Which groups should Manage actions target?", kb_scope(scope_pref.get(uid, "made")))
    elif d in ("scope_made", "scope_all"): scope_pref[uid] = d[6:]; await edit(H("🎯 Scope") + f"Scope set to **{d[6:]}**", kb_scope(d[6:]))
    elif d in ("mg_link", "mg_list", "mg_kickbots", "mg_leave"): await q.answer(); await run_manage(m, uid, d[3:], "")
    elif d == "mg_delete": await run_manage(m, uid, "delete", "")
    elif d == "confirm_delete": await q.answer(); await run_manage(m, uid, "delete", "confirm")
    elif d in ("mg_kick", "mg_add", "mg_promote", "mg_demote", "mg_rename", "mg_desc"):
        prompts = {"kick": "Send usernames to **kick** from all GCs:\n`@a @b @c`",
                   "add": "Send usernames to **add** to all GCs:\n`@a @b`",
                   "promote": "Send usernames to **promote (full admin)** in all GCs:\n`@a @b`",
                   "demote": "Send usernames to **demote** in all GCs:\n`@a @b`",
                   "rename": "Send the **new name** for all GCs:",
                   "desc": "Send the **new description** for all GCs:"}
        state[uid] = {"step": "mg_input", "cmd": d[3:]}
        await edit(H(f"🛠 {d[3:].title()}") + prompts[d[3:]], kb_cancel())
    elif d == "mg_setpic":
        state[uid] = {"step": "mg_photo"}; await edit(H("🖼 Set Photo") + "Send the photo to set on all GCs.", kb_cancel())

    # broadcast
    elif d == "bc": await edit(bc_text(uid), kb_bc(bc_cfg(uid)))
    elif d == "bc_status": await edit(bc_text(uid), kb_bc(bc_cfg(uid)))
    elif d == "bc_off": bc_cfg(uid)["on"] = False; await edit(bc_text(uid), kb_bc(bc_cfg(uid)))
    elif d in ("bc_mode_copy", "bc_mode_forward"): bc_cfg(uid)["mode"] = d[8:]; await edit(bc_text(uid), kb_bc(bc_cfg(uid)))
    elif d in ("bc_on_made", "bc_on_all"):
        r = await bc_enable(uid, d[6:]); await edit(H("📢 Broadcast System") + r, kb_bc(bc_cfg(uid)))
    elif d == "bc_on_folder":
        c = await get_user_client(uid)
        if not c: return await q.answer("Login first", show_alert=True)
        fl = await get_folders(c)
        if not fl: return await q.answer("No folders found", show_alert=True)
        names = list(fl.keys())[:20]
        state[uid] = {"step": "bc_folder_pick", "names": names}
        rows = [[IKB(f"📂 {n} ({len(fl[n])})", f"bcf_{i}")] for i, n in enumerate(names)] + [[IKB("⬅️ Back", "bc")]]
        await edit(H("📂 Pick a folder") + "Broadcast will target all groups in the chosen folder.", IKM(rows))
    elif d.startswith("bcf_"):
        st = state.pop(uid, None)
        if not st or st.get("step") != "bc_folder_pick": return await q.answer("Expired, pick again", show_alert=True)
        r = await bc_enable(uid, "folder", st["names"][int(d[4:])]); await edit(H("📢 Broadcast System") + r, kb_bc(bc_cfg(uid)))

    # access
    elif d == "access":
        if uid != OWNER_ID: return await q.answer("Owner only", show_alert=True)
        await edit(access_text(), kb_access())
    elif d in ("acc_add", "acc_del", "acc_list"):
        if uid != OWNER_ID: return await q.answer("Owner only", show_alert=True)
        if d == "acc_list": return await edit(access_text(), kb_access())
        state[uid] = {"step": "acc_input", "cmd": "auth" if d == "acc_add" else "unauth"}
        await edit(H("👑 Access Control") + f"Send the user ID(s) to **{'allow' if d == 'acc_add' else 'remove'}**:", kb_cancel())
    try: await q.answer()
    except Exception: pass

# ══════════════════════════ WIZARD TEXT / MEDIA INPUT ══════════════════════════
@bot.on_message(allowed & filters.private & filters.photo & filters.create(lambda _, __, m: state.get(m.from_user.id, {}).get("step") == "mg_photo"))
async def wizard_photo(_, m: Message):
    uid = m.from_user.id; state.pop(uid, None)
    c = await get_user_client(uid)
    ids = await target_groups(c, uid)
    if not ids: return await m.reply("❌ No target GCs.", reply_markup=kb_manage())
    path = await m.download()
    await for_each_group(m, ids, "Set Photo", lambda gid: c.set_chat_photo(gid, photo=path))
    try: os.remove(path)
    except Exception: pass

@bot.on_message(allowed & filters.text & filters.private & ~filters.regex(r"^[./]"))
async def wizard_text(_, m: Message):
    uid = m.from_user.id
    st = state.get(uid)
    if not st: return
    step, txt = st["step"], m.text.strip()

    if step == "phone":
        phone = txt.replace(" ", "")
        if not re.match(r"^\+?\d{7,15}$", phone): return await m.reply("❌ Invalid number, try again.", reply_markup=kb_cancel())
        c = Client(f"login_{uid}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
        await c.connect()
        try: sent = await c.send_code(phone)
        except FloodWait as e:
            await c.disconnect(); state.pop(uid, None); return await m.reply(f"⏳ FloodWait: try again in {e.value}s.", reply_markup=kb_back())
        except Exception as e:
            await c.disconnect(); state.pop(uid, None); return await m.reply(f"❌ Error: `{e}`", reply_markup=kb_back())
        st.update({"step": "otp", "client": c, "phone": phone, "hash": sent.phone_code_hash})
        return await m.reply(H("🔐 Login · OTP") + "Telegram sent you a code. Send it **with spaces** so it doesn't expire:\n`1 2 3 4 5`", reply_markup=kb_cancel())

    if step == "otp":
        c = st["client"]
        try: await c.sign_in(st["phone"], st["hash"], txt.replace(" ", "").replace("-", ""))
        except SessionPasswordNeeded:
            st["step"] = "password"; return await m.reply(H("🔐 Login · 2FA") + "Two-step verification is enabled. Send your **password**.", reply_markup=kb_cancel())
        except (PhoneCodeInvalid, PhoneCodeExpired): return await m.reply("❌ Wrong or expired code. Send it again.", reply_markup=kb_cancel())
        except Exception as e:
            await c.disconnect(); state.pop(uid, None); return await m.reply(f"❌ Error: `{e}`", reply_markup=kb_back())
        return await finish_login(m, uid, c)

    if step == "password":
        c = st["client"]
        try: await c.check_password(txt)
        except PasswordHashInvalid: return await m.reply("❌ Wrong password. Try again.", reply_markup=kb_cancel())
        except Exception as e:
            await c.disconnect(); state.pop(uid, None); return await m.reply(f"❌ Error: `{e}`", reply_markup=kb_back())
        return await finish_login(m, uid, c)

    if step == "folder_q":
        t = txt.lower()
        if t not in ("folder", "normal"): return await m.reply("Reply `folder` or `normal`, or use the buttons.")
        return await gc_ask_count(m, uid, t == "folder")
    if step == "count":
        if not txt.isdigit() or not (1 <= int(txt) <= 50): return await m.reply("❌ Send a number between 1 and 50.", reply_markup=kb_cancel())
        return await gc_ask_members(m, uid, int(txt))
    if step == "members":
        st["members"] = [] if txt.lower() == "skip" else parse_users(txt)
        state.pop(uid, None); return await run_gc_job(m, uid, st)

    if step == "mg_input":
        state.pop(uid, None); return await run_manage(m, uid, st["cmd"], txt)
    if step == "acc_input":
        state.pop(uid, None)
        if uid != OWNER_ID: return
        ids = [int(x) for x in re.split(r"[\s,]+", txt) if x.strip().isdigit()]
        if not ids: return await m.reply("❌ Send numeric user IDs.", reply_markup=kb_access())
        sudo = load_sudo()
        if st["cmd"] == "auth": sudo |= set(ids)
        else: sudo -= set(ids)
        save_sudo(sudo); return await m.reply(access_text(), reply_markup=kb_access())

# ══════════════════════════ KEEP-ALIVE WEB SERVER (Render + UptimeRobot) ══════════════════════════
async def _health(_): return web.Response(text=f"{BRAND} | controller online ✅")

async def start_web():
    app = web.Application(); app.router.add_get("/", _health); app.router.add_get("/health", _health)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    log.info(f"keep-alive server on :{PORT}")

async def main():
    await start_web()
    await bot.start()
    me = await bot.get_me()
    log.info(f"{BRAND} online as @{me.username} | owner {OWNER_ID} | sudo {load_sudo()}")
    for uid in list(_load(SESS_FILE, {}).keys()):     # pre-warm saved sessions
        try: await get_user_client(int(uid))
        except Exception as e: log.warning(f"warm {uid}: {e}")
    await idle()
    await bot.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
