#!/usr/bin/env python3

from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty, InputPeerUser
from telethon.errors.rpcerrorlist import (
    PeerFloodError,
    UserPrivacyRestrictedError,
    FloodWaitError,
    UserNotMutualContactError,
    UserBannedInChannelError,
    ChatWriteForbiddenError,
    UserAlreadyParticipantError,
)
from telethon.tl.functions.channels import InviteToChannelRequest
import time
import random
import asyncio
import json
import os

# --- Konfigurasi --- #
api_id   = 26372402
api_hash = 'a2732d77a9abc513db065170f563a603'
phone    = '+6285962694573'

# --- Batas keamanan --- #
BATCH_SIZE      = 5    # Jeda panjang setiap berapa penambahan
BATCH_REST_MIN  = 300  # Jeda panjang minimum (detik) = 5 menit
BATCH_REST_MAX  = 600  # Jeda panjang maksimum (detik) = 10 menit
DELAY_MIN       = 60   # Jeda minimum antar tambah (detik)
DELAY_MAX       = 120  # Jeda maksimum antar tambah (detik)
PROGRESS_FILE   = 'autopilot_progress.json'

client = TelegramClient(phone, api_id, api_hash)

# ── Simpan & muat progress ────────────────────────────────────────────────────

def save_progress(target_group_id, my_group_id, done_ids):
    data = {
        'target_group_id': target_group_id,
        'my_group_id': my_group_id,
        'done_ids': list(done_ids),
    }
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(data, f)

def load_progress():
    if not os.path.exists(PROGRESS_FILE):
        return None
    with open(PROGRESS_FILE) as f:
        return json.load(f)

def clear_progress():
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print("--- Telegram Auto Pilot (Scrape & Add) ---")
    await client.connect()

    if not await client.is_user_authorized():
        await client.send_code_request(phone)
        await client.sign_in(phone, input("Masukkan kode verifikasi dari Telegram: "))

    me = await client.get_me()
    print(f"Login sebagai: {me.first_name} (@{me.username})")

    # ── Cek progress tersimpan ────────────────────────────────────────────────
    saved = load_progress()
    resume_mode = False

    if saved:
        print(f"\n⚡ Ditemukan progress sebelumnya!")
        print(f"   Sudah diproses: {len(saved['done_ids'])} orang")
        jawab = input("   Lanjut dari sesi terakhir? (y/n): ").strip().lower()
        if jawab == 'y':
            resume_mode = True
        else:
            clear_progress()
            saved = None

    # ── TAHAP 1: SCRAPING ─────────────────────────────────────────────────────
    if not resume_mode:
        print("\n[1] TAHAP SCRAPING")
        target_url = input(
            "Masukkan username/link grup TARGET (contoh: nanomilkiss): "
        ).replace("https://t.me/", "").replace("@", "").strip()

        try:
            target_group = await client.get_entity(target_url)
            print(f"Mengambil anggota dari: {target_group.title}...")
            all_participants = await client.get_participants(target_group, aggressive=True)
            print(f"Berhasil mengambil {len(all_participants)} anggota.")
        except Exception as e:
            print(f"Gagal mengambil grup target: {e}")
            return

        candidates = [
            u for u in all_participants
            if u.username and not getattr(u, 'bot', False) and u.id != me.id
        ]
        print(f"Kandidat (punya username, bukan bot): {len(candidates)}")

        # ── TAHAP 2: PILIH GRUP TUJUAN ────────────────────────────────────────
        print("\n[2] PILIH GRUP TUJUAN ANDA")
        result = await client(GetDialogsRequest(
            offset_date=None, offset_id=0,
            offset_peer=InputPeerEmpty(), limit=200, hash=0
        ))
        groups = [c for c in result.chats if getattr(c, 'megagroup', False)]
        for i, g in enumerate(groups):
            print(f"{i}- {g.title}")

        g_index = int(input("Pilih nomor grup TUJUAN Anda: "))
        my_group = groups[g_index]

        done_ids = set()
        target_group_id = target_group.id
        my_group_id = my_group.id

    else:
        # Resume — load ulang data dari Telegram
        print("\n[1] MEMUAT ULANG DATA...")
        target_group = await client.get_entity(saved['target_group_id'])
        print(f"Mengambil anggota dari: {target_group.title}...")
        all_participants = await client.get_participants(target_group, aggressive=True)

        candidates = [
            u for u in all_participants
            if u.username and not getattr(u, 'bot', False) and u.id != me.id
        ]

        my_group = await client.get_entity(saved['my_group_id'])
        done_ids = set(saved['done_ids'])
        target_group_id = saved['target_group_id']
        my_group_id = saved['my_group_id']

        sisa = [u for u in candidates if u.id not in done_ids]
        print(f"Sisa yang belum diproses: {len(sisa)} dari {len(candidates)}")
        candidates = sisa

    # ── TAHAP 3: PENAMBAHAN ───────────────────────────────────────────────────
    print(f"\n[3] TAHAP PENAMBAHAN (Grup Tujuan: {my_group.title})")
    print(f"Mode             : Unlimited (semua kandidat)")
    print(f"Jeda antar tambah: {DELAY_MIN}–{DELAY_MAX} detik")
    print(f"Jeda antar batch : {BATCH_REST_MIN//60}–{BATCH_REST_MAX//60} menit (setiap {BATCH_SIZE} orang)\n")

    added_count = 0
    skip_count  = 0
    total       = len(candidates)

    for user in candidates:
        try:
            user_to_add = InputPeerUser(user.id, user.access_hash)
            await client(InviteToChannelRequest(my_group, [user_to_add]))

            added_count += 1
            done_ids.add(user.id)
            save_progress(target_group_id, my_group_id, done_ids)
            print(f"[{added_count}/{total}] ✔ Ditambahkan: {user.first_name or ''} (@{user.username})")

            if added_count % BATCH_SIZE == 0:
                rest = random.randint(BATCH_REST_MIN, BATCH_REST_MAX)
                print(f"\n⏸  Istirahat batch — menunggu {rest // 60} menit {rest % 60} detik...\n")
                time.sleep(rest)
            else:
                wait = random.randint(DELAY_MIN, DELAY_MAX)
                print(f"   Menunggu {wait} detik...")
                time.sleep(wait)

        except FloodWaitError as e:
            print(f"\n⚠️  FloodWait: Telegram minta tunggu {e.seconds} detik ({e.seconds // 60} menit).")
            print("   Menunggu sesuai permintaan Telegram...")
            time.sleep(e.seconds + 10)

        except PeerFloodError:
            print("\n🚫 PeerFloodError: Akun terkena pembatasan Telegram.")
            print(f"   Progress disimpan — sudah diproses {len(done_ids)} orang.")
            print("   Tunggu 24–48 jam, lalu jalankan ulang dan pilih 'y' untuk lanjut.")
            save_progress(target_group_id, my_group_id, done_ids)
            break

        except UserAlreadyParticipantError:
            skip_count += 1
            done_ids.add(user.id)
            print(f"   SKIP (sudah di grup): @{user.username}")

        except UserPrivacyRestrictedError:
            skip_count += 1
            done_ids.add(user.id)
            print(f"   SKIP (privasi): @{user.username}")

        except (UserNotMutualContactError, UserBannedInChannelError):
            skip_count += 1
            done_ids.add(user.id)
            print(f"   SKIP (tidak bisa ditambah): @{user.username}")

        except ChatWriteForbiddenError:
            print("\n🚫 Tidak punya izin menambah anggota ke grup ini.")
            break

        except Exception as e:
            print(f"   ERROR pada @{user.username}: {e}")
            time.sleep(15)

    else:
        # Loop selesai normal (semua kandidat diproses)
        clear_progress()
        print("\n✅ Semua kandidat sudah diproses! Progress dihapus.")

    print(f"\n{'='*45}")
    print(f"Selesai! Ditambahkan: {added_count} | Diskip: {skip_count}")
    print(f"{'='*45}")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
