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
)
from telethon.tl.functions.channels import InviteToChannelRequest
import time
import random
import asyncio

# --- Konfigurasi --- #
api_id   = 26372402
api_hash = 'a2732d77a9abc513db065170f563a603'
phone    = '+6285962694573'

# --- Batas keamanan --- #
MAX_PER_SESSION  = 10    # Maksimal tambah per sekali jalan (turunkan jika masih kena ban)
BATCH_SIZE       = 5     # Setelah berapa penambahan, ambil jeda panjang
BATCH_REST_MIN   = 300   # Jeda panjang minimum setelah 1 batch (detik) = 5 menit
BATCH_REST_MAX   = 600   # Jeda panjang maksimum setelah 1 batch (detik) = 10 menit
DELAY_MIN        = 60    # Jeda minimum antar penambahan (detik)
DELAY_MAX        = 120   # Jeda maksimum antar penambahan (detik)

client = TelegramClient(phone, api_id, api_hash)

async def main():
    print("--- Telegram Auto Pilot (Scrape & Add) ---")
    await client.connect()

    if not await client.is_user_authorized():
        await client.send_code_request(phone)
        await client.sign_in(phone, input("Masukkan kode verifikasi dari Telegram: "))

    # ── TAHAP 1: SCRAPING ──────────────────────────────────────────────────
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

    # Filter: hanya user yang punya username, bukan bot
    candidates = [
        u for u in all_participants
        if u.username and not getattr(u, 'bot', False)
    ]
    print(f"Kandidat yang bisa ditambahkan (punya username, bukan bot): {len(candidates)}")

    # ── TAHAP 2: PILIH GRUP TUJUAN ─────────────────────────────────────────
    print("\n[2] PILIH GRUP TUJUAN ANDA")
    result = await client(GetDialogsRequest(
        offset_date=None,
        offset_id=0,
        offset_peer=InputPeerEmpty(),
        limit=200,
        hash=0
    ))
    groups = [c for c in result.chats if getattr(c, 'megagroup', False)]

    for i, g in enumerate(groups):
        print(f"{i}- {g.title}")

    g_index = int(input("Pilih nomor grup TUJUAN Anda: "))
    my_group = groups[g_index]

    # ── TAHAP 3: PENAMBAHAN ────────────────────────────────────────────────
    print(f"\n[3] TAHAP PENAMBAHAN (Grup Tujuan: {my_group.title})")
    print(f"Batas sesi ini   : {MAX_PER_SESSION} orang")
    print(f"Jeda antar tambah: {DELAY_MIN}–{DELAY_MAX} detik")
    print(f"Jeda antar batch : {BATCH_REST_MIN//60}–{BATCH_REST_MAX//60} menit (setiap {BATCH_SIZE} orang)\n")

    added_count = 0
    skip_count  = 0

    for user in candidates:
        if added_count >= MAX_PER_SESSION:
            print(f"\n✅ Batas sesi ({MAX_PER_SESSION} orang) tercapai.")
            print("Jalankan lagi besok atau beberapa jam lagi untuk melanjutkan.")
            break

        try:
            user_to_add = InputPeerUser(user.id, user.access_hash)
            await client(InviteToChannelRequest(my_group, [user_to_add]))

            added_count += 1
            print(f"[{added_count}/{MAX_PER_SESSION}] ✔ Ditambahkan: {user.first_name or ''} (@{user.username})")

            # Jeda panjang setiap BATCH_SIZE penambahan
            if added_count % BATCH_SIZE == 0 and added_count < MAX_PER_SESSION:
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
            time.sleep(e.seconds + 10)  # +10 detik buffer

        except PeerFloodError:
            print("\n🚫 PeerFloodError: Akun terkena pembatasan Telegram.")
            print("   Hentikan skrip dan tunggu minimal 24–48 jam sebelum mencoba lagi.")
            break

        except UserPrivacyRestrictedError:
            skip_count += 1
            print(f"   SKIP (privasi): @{user.username}")

        except (UserNotMutualContactError, UserBannedInChannelError):
            skip_count += 1
            print(f"   SKIP (tidak bisa ditambah): @{user.username}")

        except ChatWriteForbiddenError:
            print("\n🚫 Tidak punya izin menambah anggota ke grup ini.")
            break

        except Exception as e:
            print(f"   ERROR pada @{user.username}: {e}")
            time.sleep(15)

    print(f"\n{'='*45}")
    print(f"Selesai! Ditambahkan: {added_count} | Diskip: {skip_count}")
    print(f"{'='*45}")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
