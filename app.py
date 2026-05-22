import streamlit as st
from collections import deque
import pandas as pd

# ---------------------------- Data Model ----------------------------
class Member:
    def __init__(self, id, name, sponsor_id, parent_id=None, is_active=True):
        self.id = id
        self.name = name
        self.sponsor_id = sponsor_id          # untuk Auto Rich
        self.parent_id = parent_id            # untuk Auto Cuan (placement)
        self.left_child_id = None
        self.right_child_id = None
        self.is_active = is_active
        self.balance_cuan = 0
        self.balance_rich = 0
        self.total_spent = 0

# ---------------------------- Helper Functions ----------------------------
def init_session():
    if 'members' not in st.session_state:
        root = Member(1, "Perusahaan", sponsor_id=None, parent_id=None, is_active=True)
        st.session_state.members = {1: root}
        st.session_state.next_id = 2
        st.session_state.total_cash_in = 0
        st.session_state.total_bonus_cuan = 0
        st.session_state.total_bonus_rich = 0

def find_placement_cuan(start_id, members):
    """
    Mencari posisi kosong untuk Auto Cuan (binary tree, prioritas kanan).
    Kembalikan (parent_id, is_left) dengan is_left=True untuk anak kiri, False untuk kanan.
    """
    queue = deque([start_id])
    while queue:
        node_id = queue.popleft()
        node = members[node_id]
        # Prioritas kanan
        if node.right_child_id is None:
            return node_id, False
        if node.left_child_id is None:
            return node_id, True
        # Jika penuh, lanjutkan BFS (kanan dulu)
        if node.right_child_id:
            queue.append(node.right_child_id)
        if node.left_child_id:
            queue.append(node.left_child_id)
    return start_id, True  # fallback

def register_member(sponsor_id, name):
    """
    Registrasi member baru.
    Auto Rich: sponsor = sponsor_id (langsung, tanpa spillover)
    Auto Cuan: placement = hasil find_placement_cuan(sponsor_id)
    """
    members = st.session_state.members
    # Validasi sponsor
    if sponsor_id not in members:
        return None, f"Sponsor ID {sponsor_id} tidak ditemukan."
    
    new_id = st.session_state.next_id
    st.session_state.next_id += 1
    
    # Cari parent untuk Auto Cuan (placement tree)
    parent_id, is_left = find_placement_cuan(sponsor_id, members)
    
    # Buat member baru
    new_member = Member(new_id, name, sponsor_id, parent_id, is_active=True)
    members[new_id] = new_member
    
    # Update hubungan di parent (Auto Cuan)
    parent = members[parent_id]
    if not is_left:
        parent.right_child_id = new_id
    else:
        parent.left_child_id = new_id
    
    posisi = "kanan" if not is_left else "kiri"
    info = (f"✅ Auto Cuan: anak {posisi} dari {parent.name} (ID:{parent.id})\n"
            f"✅ Auto Rich: sponsor langsung = {members[sponsor_id].name} (ID:{sponsor_id})")
    return new_member, info

def get_ancestors_cuan(member_id, members, max_level=7):
    ancestors = []
    cur = members[member_id].parent_id
    level = 1
    while cur and level <= max_level:
        ancestors.append((cur, level))
        cur = members[cur].parent_id
        level += 1
    return ancestors

def get_ancestors_rich(member_id, members, max_level=7):
    ancestors = []
    cur = members[member_id].sponsor_id
    level = 1
    while cur and level <= max_level:
        ancestors.append((cur, level))
        cur = members[cur].sponsor_id
        level += 1
    return ancestors

def process_transaction(member_id, amount, apply_to_balance=False):
    members = st.session_state.members
    if member_id not in members:
        return None
    member = members[member_id]
    if amount >= 100000:
        member.is_active = True
    else:
        member.is_active = False
    if apply_to_balance:
        member.total_spent += amount
        st.session_state.total_cash_in += amount

    # Auto Cuan
    bonus_cuan = 0
    breakdown_cuan = []
    if member.is_active:
        ancestors = get_ancestors_cuan(member_id, members)
        valid = []
        for anc_id, lvl in ancestors:
            if members[anc_id].is_active:
                valid.append((anc_id, lvl))
            else:
                break
        n = len(valid)
        for i, (anc_id, lvl) in enumerate(valid):
            komisi = 9000 if i == n-1 else 4000
            if apply_to_balance:
                members[anc_id].balance_cuan += komisi
                st.session_state.total_bonus_cuan += komisi
            bonus_cuan += komisi
            breakdown_cuan.append((anc_id, f"Matrix Lv{lvl} ({'Last' if i==n-1 else 'Reg'})", komisi))
    # Bonus sponsor
    sponsor_id = member.sponsor_id
    if sponsor_id and sponsor_id in members:
        komisi_sp = 1000
        if apply_to_balance:
            members[sponsor_id].balance_cuan += komisi_sp
            st.session_state.total_bonus_cuan += komisi_sp
        bonus_cuan += komisi_sp
        breakdown_cuan.append((sponsor_id, "Bonus Sponsor", komisi_sp))

    # Auto Rich
    bonus_rich = 0
    breakdown_rich = []
    ancestors_rich = get_ancestors_rich(member_id, members)
    for anc_id, lvl in ancestors_rich:
        komisi = 5000
        if apply_to_balance:
            members[anc_id].balance_rich += komisi
            st.session_state.total_bonus_rich += komisi
        bonus_rich += komisi
        breakdown_rich.append((anc_id, f"Level {lvl}", komisi))

    return {
        'buyer_name': member.name, 'buyer_id': member_id, 'amount': amount,
        'member_active': member.is_active,
        'bonus_cuan': bonus_cuan, 'bonus_rich': bonus_rich,
        'total_bonus': bonus_cuan + bonus_rich,
        'breakdown_cuan': breakdown_cuan, 'breakdown_rich': breakdown_rich
    }

def get_member_tree_cuan(root_id, members):
    if root_id not in members:
        return ""
    lines = []
    queue = deque([root_id])
    while queue:
        nid = queue.popleft()
        node = members[nid]
        label = f"{node.name} (ID:{nid})\n{'Aktif' if node.is_active else 'Tdk Aktif'}"
        lines.append(f'    "{nid}" [label="{label}"];')
        if node.left_child_id:
            lines.append(f'    "{nid}" -> "{node.left_child_id}";')
            queue.append(node.left_child_id)
        if node.right_child_id:
            lines.append(f'    "{nid}" -> "{node.right_child_id}";')
            queue.append(node.right_child_id)
    return "digraph G {\n" + "\n".join(lines) + "\n}"

def get_member_tree_rich(root_id, members):
    if root_id not in members:
        return ""
    lines = []
    for nid, node in members.items():
        lines.append(f'    "{nid}" [label="{node.name} (ID:{nid})\\nSaldo R: {node.balance_rich:,}"];')
    for nid, node in members.items():
        if node.sponsor_id and node.sponsor_id in members:
            lines.append(f'    "{node.sponsor_id}" -> "{nid}";')
    return "digraph G {\n" + "\n".join(lines) + "\n}"

def create_sample_10_binary():
    """Membuat 10 member dengan sponsor = Perusahaan (ID 1)"""
    members = st.session_state.members
    if len(members) > 1:
        st.warning("Jaringan sudah memiliki member. Reset terlebih dahulu.")
        return
    for i in range(1, 11):
        name = f"Member {i}"
        new, info = register_member(1, name)
        if new:
            st.success(f"{name} (ID:{new.id}) berhasil.")
        else:
            st.error(f"Gagal: {info}")
    st.info("Sample 10 member (sponsor=Perusahaan) selesai. Cek visualisasi Auto Cuan dan Auto Rich.")

def reset_app():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.clear()
    init_session()
    st.rerun()

# ---------------------------- UI Streamlit ----------------------------
def main():
    st.set_page_config(page_title="K-BBPT Simulator", layout="wide")
    st.title("K-BBPT Simulator Jaringan & Komisi")
    st.markdown("**Auto Cuan** (Binary + Spillover prioritas kanan) | **Auto Rich** (Unlimited Direct)")
    init_session()

    with st.sidebar:
        st.header("🛠️ Sample")
        if st.button("🌳 Sample 10 Member Binary", use_container_width=True):
            create_sample_10_binary()
        if st.button("🗑️ Reset Aplikasi", use_container_width=True):
            reset_app()
        st.markdown("---")
        menu = st.selectbox("Menu", ["Dashboard", "Registrasi Member", "Simulasi Transaksi", "Visualisasi Jaringan"])

    members = st.session_state.members

    if menu == "Dashboard":
        st.header("📊 Ringkasan Simulasi")
        col1, col2, col3 = st.columns(3)
        total_member = len(members)
        active_member = sum(1 for m in members.values() if m.is_active)
        col1.metric("Total Member", total_member)
        col2.metric("Member Aktif (Auto Cuan)", active_member)
        col3.metric("Total Cash In (Rp)", f"{st.session_state.total_cash_in:,.0f}")
        col4, col5, col6 = st.columns(3)
        col4.metric("Total Bonus Auto Cuan (Rp)", f"{st.session_state.total_bonus_cuan:,.0f}")
        col5.metric("Total Bonus Auto Rich (Rp)", f"{st.session_state.total_bonus_rich:,.0f}")
        nett = st.session_state.total_cash_in - (st.session_state.total_bonus_cuan + st.session_state.total_bonus_rich)
        col6.metric("Nett Perusahaan (Rp)", f"{nett:,.0f}")

        st.subheader("🔍 Alur Komisi (Simulasi tanpa mengubah saldo)")
        sim_member = st.selectbox("Pilih member yang bertransaksi", options=list(members.keys()), format_func=lambda x: f"{members[x].name} (ID:{x})")
        sim_amount = st.number_input("Nominal Belanja (Rp)", min_value=0, step=10000, value=100000)
        if st.button("Tampilkan Alur Komisi"):
            res = process_transaction(sim_member, sim_amount, apply_to_balance=False)
            if res:
                st.markdown(f"**Pembeli:** {res['buyer_name']} (ID:{res['buyer_id']}) | **Belanja:** Rp{res['amount']:,.0f}")
                st.markdown(f"**Status Auto Cuan pembeli:** {'✅ Aktif' if res['member_active'] else '❌ Tidak Aktif'}")
                with st.expander("Auto Cuan (Matrix + Sponsor)", expanded=True):
                    if res['breakdown_cuan']:
                        df_c = pd.DataFrame(res['breakdown_cuan'], columns=["Member ID", "Jenis", "Rp"])
                        st.dataframe(df_c, use_container_width=True)
                        st.write(f"**Total:** Rp{res['bonus_cuan']:,.0f}")
                    else:
                        st.write("Tidak ada komisi.")
                with st.expander("Auto Rich (Flat Rp5.000/ancestor)", expanded=True):
                    if res['breakdown_rich']:
                        df_r = pd.DataFrame(res['breakdown_rich'], columns=["Member ID", "Level", "Rp"])
                        st.dataframe(df_r, use_container_width=True)
                        st.write(f"**Total:** Rp{res['bonus_rich']:,.0f}")
                    else:
                        st.write("Tidak ada komisi.")
                st.success(f"**Total komisi:** Rp{res['total_bonus']:,.0f}")

        st.subheader("📋 Daftar Member")
        df_data = []
        for m in members.values():
            df_data.append({
                "ID": m.id, "Nama": m.name, "Sponsor (Auto Rich)": m.sponsor_id,
                "Parent Cuan": m.parent_id, "Status": "✅" if m.is_active else "❌",
                "Balance Cuan": m.balance_cuan, "Balance Rich": m.balance_rich,
                "Total Belanja": m.total_spent
            })
        st.dataframe(pd.DataFrame(df_data), use_container_width=True)

    elif menu == "Registrasi Member":
        st.header("📝 Registrasi Member Baru")
        with st.form("register_form"):
            name = st.text_input("Nama Lengkap")
            # Buat list pilihan sponsor (ID dan nama)
            sponsor_list = [(m.id, f"{m.name} (ID:{m.id})") for m in members.values()]
            sponsor_id = st.selectbox("Pilih Sponsor", options=sponsor_list, format_func=lambda x: x[1])[0]
            submitted = st.form_submit_button("Daftarkan")
            if submitted:
                if not name.strip():
                    st.error("Nama tidak boleh kosong")
                else:
                    new, info = register_member(sponsor_id, name.strip())
                    if new:
                        st.success(f"Member {new.name} (ID:{new.id}) berhasil didaftarkan!")
                        st.info(info)
                        # Debug: tampilkan sponsor yang digunakan
                        st.write(f"**Debug:** sponsor_id yang dipilih = {sponsor_id} ({members[sponsor_id].name})")
                    else:
                        st.error(info)

    elif menu == "Simulasi Transaksi":
        st.header("💰 Simulasi Transaksi (menambah saldo)")
        member_options = {m.id: f"{m.name} (ID:{m.id})" for m in members.values()}
        member_id = st.selectbox("Pilih member", options=list(member_options.keys()), format_func=lambda x: member_options[x])
        amount = st.number_input("Nominal Belanja (Rp)", min_value=0, step=10000, value=100000)
        if st.button("Proses & Tambahkan Komisi"):
            res = process_transaction(member_id, amount, apply_to_balance=True)
            if res:
                st.success(f"Transaksi Rp{amount:,.0f} oleh {members[member_id].name}")
                st.write(f"**Status Auto Cuan:** {'Aktif' if res['member_active'] else 'Tidak'}")
                st.write(f"**Bonus Auto Cuan:** Rp{res['bonus_cuan']:,.0f}")
                st.write(f"**Bonus Auto Rich:** Rp{res['bonus_rich']:,.0f}")
                st.write(f"**Total komisi:** Rp{res['total_bonus']:,.0f}")
            else:
                st.error("Member tidak valid")

    elif menu == "Visualisasi Jaringan":
        st.header("🌳 Visualisasi Jaringan")
        net_type = st.radio("Pilih jenis jaringan", ["Auto Cuan (Binary / Placement)", "Auto Rich (Sponsor Tree)"])
        root_options = {m.id: f"{m.name} (ID:{m.id})" for m in members.values()}
        root_id = st.selectbox("Root / Member awal", options=list(root_options.keys()), format_func=lambda x: root_options[x])
        if net_type == "Auto Cuan (Binary / Placement)":
            dot = get_member_tree_cuan(root_id, members)
        else:
            dot = get_member_tree_rich(root_id, members)
        if dot:
            st.graphviz_chart(dot)
        else:
            st.warning("Pohon kosong atau root tidak ditemukan")

if __name__ == "__main__":
    main()
