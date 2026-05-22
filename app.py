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

def find_placement_cuan(sponsor_id, members):
    """Binary tree prioritas kanan"""
    queue = deque([sponsor_id])
    while queue:
        node_id = queue.popleft()
        node = members[node_id]
        if node.right_child_id is None:
            return node_id, False
        if node.left_child_id is None:
            return node_id, True
        if node.right_child_id:
            queue.append(node.right_child_id)
        if node.left_child_id:
            queue.append(node.left_child_id)
    return sponsor_id, True

def register_member(sponsor_id, name):
    members = st.session_state.members
    if sponsor_id not in members:
        return None
    new_id = st.session_state.next_id
    st.session_state.next_id += 1
    parent_id, is_left = find_placement_cuan(sponsor_id, members)
    new_member = Member(new_id, name, sponsor_id, parent_id, is_active=True)
    members[new_id] = new_member
    parent = members[parent_id]
    if not is_left:
        parent.right_child_id = new_id
    else:
        parent.left_child_id = new_id
    return new_member

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
    # Update status aktif berdasarkan belanja (Auto Cuan)
    if amount >= 100000:
        member.is_active = True
    else:
        member.is_active = False

    if apply_to_balance:
        member.total_spent += amount
        st.session_state.total_cash_in += amount

    # ---- Auto Cuan (Matrix + Bonus Sponsor) ----
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
            breakdown_cuan.append((anc_id, f"Matrix Level {lvl} ({'Last Ancestor' if i==n-1 else 'Reguler'})", komisi))
    # Bonus sponsor (Rp1000 untuk sponsor langsung pembayar)
    sponsor_id = member.sponsor_id
    if sponsor_id and sponsor_id in members:
        komisi_sp = 1000
        if apply_to_balance:
            members[sponsor_id].balance_cuan += komisi_sp
            st.session_state.total_bonus_cuan += komisi_sp
        bonus_cuan += komisi_sp
        breakdown_cuan.append((sponsor_id, "Bonus Sponsor Langsung", komisi_sp))

    # ---- Auto Rich (Flat Rp5000 per ancestor sponsor tree) ----
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
        'buyer_name': member.name,
        'buyer_id': member_id,
        'amount': amount,
        'member_active': member.is_active,
        'bonus_cuan': bonus_cuan,
        'bonus_rich': bonus_rich,
        'total_bonus': bonus_cuan + bonus_rich,
        'breakdown_cuan': breakdown_cuan,
        'breakdown_rich': breakdown_rich
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
        lines.append(f'    "{nid}" [label="{node.name} (ID:{nid})\\nSaldo: {node.balance_rich:,}"];')
    for nid, node in members.items():
        if node.sponsor_id and node.sponsor_id in members:
            lines.append(f'    "{node.sponsor_id}" -> "{nid}";')
    return "digraph G {\n" + "\n".join(lines) + "\n}"

def create_sample_network_basic():
    """Jaringan 6 member seperti sebelumnya (jalur kanan)"""
    members = st.session_state.members
    if len(members) > 1:
        st.warning("Jaringan sudah memiliki member. Reset terlebih dahulu.")
        return
    register_member(1, "Member 1")   # ID2
    register_member(1, "Member 2")   # ID3
    register_member(2, "Member 3")   # ID4
    register_member(2, "Member 4")   # ID5
    register_member(4, "Member 5")   # ID6
    register_member(6, "Member 6")   # ID7
    st.success("Sample 6 member (jalur kanan) siap!")

def create_sample_network_10():
    """
    Membangun 10 member dengan skenario:
    - Auto Cuan: tetap mengikuti spillover prioritas kanan (binary tree)
    - Auto Rich: sponsor dipilih secara bebas untuk menunjukkan perbedaan
    Member dan sponsor (untuk Auto Rich):
    ID 1: Perusahaan (root)
    ID 2: Member A, sponsor=1
    ID 3: Member B, sponsor=1
    ID 4: Member C, sponsor=2
    ID 5: Member D, sponsor=2
    ID 6: Member E, sponsor=3
    ID 7: Member F, sponsor=3
    ID 8: Member G, sponsor=4
    ID 9: Member H, sponsor=5
    ID 10: Member I, sponsor=6
    ID 11: Member J, sponsor=7
    """
    members = st.session_state.members
    if len(members) > 1:
        st.warning("Jaringan sudah memiliki member. Reset terlebih dahulu.")
        return

    # Buat member sesuai daftar
    register_member(1, "Member A")   # ID2
    register_member(1, "Member B")   # ID3
    register_member(2, "Member C")   # ID4
    register_member(2, "Member D")   # ID5
    register_member(3, "Member E")   # ID6
    register_member(3, "Member F")   # ID7
    register_member(4, "Member G")   # ID8
    register_member(5, "Member H")   # ID9
    register_member(6, "Member I")   # ID10
    register_member(7, "Member J")   # ID11

    st.success("Sample 10 member dengan struktur Auto Cuan & Auto Rich berbeda!")
    # Tampilkan ringkasan
    df_sponsor = []
    for m in st.session_state.members.values():
        if m.id == 1:
            continue
        df_sponsor.append({
            "Member": m.name,
            "ID": m.id,
            "Sponsor (Auto Rich)": st.session_state.members[m.sponsor_id].name if m.sponsor_id else "-",
            "Parent (Auto Cuan)": st.session_state.members[m.parent_id].name if m.parent_id else "-"
        })
    st.dataframe(pd.DataFrame(df_sponsor), use_container_width=True)
    st.info(
        "**Perhatikan:**\n"
        "- **Auto Cuan** menempatkan member berdasarkan spillover (prioritas kanan).\n"
        "- **Auto Rich** mengikuti sponsor (bisa berbeda dengan parent placement).\n"
        "Coba simulasi transaksi dari Member J (ID11) dengan nominal 100.000. Lihat perbedaan komisi antara Auto Cuan dan Auto Rich."
    )

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
    st.markdown("Auto Cuan (Binary + Spillover prioritas kanan) & Auto Rich (Unlimited Direct)")
    init_session()

    with st.sidebar:
        st.header("🛠️ Pengaturan Jaringan")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🌿 Sample 6 Member", use_container_width=True):
                create_sample_network_basic()
        with col2:
            if st.button("🌟 Sample 10 Member", use_container_width=True):
                create_sample_network_10()
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
                if not res['member_active']:
                    st.warning("Member tidak aktif (belanja < Rp100.000) → Tidak ada komisi Auto Cuan.")
                with st.expander("📌 Auto Cuan (Matrix + Sponsor)", expanded=True):
                    if res['breakdown_cuan']:
                        df_c = pd.DataFrame(res['breakdown_cuan'], columns=["Member ID", "Jenis Komisi", "Nominal (Rp)"])
                        st.dataframe(df_c, use_container_width=True)
                        st.write(f"**Total Auto Cuan:** Rp{res['bonus_cuan']:,.0f}")
                    else:
                        st.write("Tidak ada komisi Auto Cuan.")
                with st.expander("📌 Auto Rich (Flat Rp5.000 per ancestor sponsor)", expanded=True):
                    if res['breakdown_rich']:
                        df_r = pd.DataFrame(res['breakdown_rich'], columns=["Member ID", "Level Ancestor", "Nominal (Rp)"])
                        st.dataframe(df_r, use_container_width=True)
                        st.write(f"**Total Auto Rich:** Rp{res['bonus_rich']:,.0f}")
                    else:
                        st.write("Tidak ada komisi Auto Rich.")
                st.success(f"**Total komisi yang dibayarkan:** Rp{res['total_bonus']:,.0f}")

        st.subheader("📋 Daftar Member")
        df_data = []
        for m in members.values():
            df_data.append({
                "ID": m.id, "Nama": m.name, "Sponsor ID": m.sponsor_id, "Parent Cuan": m.parent_id,
                "Status Aktif": "✅" if m.is_active else "❌",
                "Balance Cuan": m.balance_cuan, "Balance Rich": m.balance_rich,
                "Total Belanja": m.total_spent
            })
        st.dataframe(pd.DataFrame(df_data), use_container_width=True)

    elif menu == "Registrasi Member":
        st.header("📝 Registrasi Member Baru (langsung aktif)")
        with st.form("register_form"):
            name = st.text_input("Nama Lengkap")
            sponsor_options = {m.id: f"{m.name} (ID:{m.id})" for m in members.values()}
            sponsor_id = st.selectbox("Pilih Sponsor (Auto Rich)", options=list(sponsor_options.keys()), format_func=lambda x: sponsor_options[x])
            if st.form_submit_button("Daftarkan"):
                if not name.strip():
                    st.error("Nama tidak boleh kosong")
                else:
                    new = register_member(sponsor_id, name.strip())
                    if new:
                        st.success(f"Member {new.name} (ID:{new.id}) aktif langsung!")
                        parent = members[new.parent_id]
                        pos = "kanan" if parent.right_child_id == new.id else "kiri"
                        st.info(f"Auto Cuan: ditempatkan sebagai anak {pos} dari {parent.name} (ID:{parent.id})")
                        st.info(f"Auto Rich: sponsor langsung = {members[sponsor_id].name}")
                    else:
                        st.error("Sponsor tidak valid")

    elif menu == "Simulasi Transaksi":
        st.header("💰 Simulasi Transaksi (menambah saldo dan cash in)")
        member_options = {m.id: f"{m.name} (ID:{m.id})" for m in members.values()}
        member_id = st.selectbox("Pilih member yang bertransaksi", options=list(member_options.keys()), format_func=lambda x: member_options[x])
        amount = st.number_input("Nominal Belanja (Rp)", min_value=0, step=10000, value=100000)
        if st.button("Proses Transaksi & Tambahkan Komisi ke Saldo"):
            res = process_transaction(member_id, amount, apply_to_balance=True)
            if res:
                st.success(f"Transaksi Rp{amount:,.0f} oleh {members[member_id].name}")
                st.write(f"**Status Auto Cuan member:** {'Aktif' if res['member_active'] else 'Tidak Aktif'}")
                st.write(f"**Bonus Auto Cuan dibayarkan:** Rp{res['bonus_cuan']:,.0f}")
                st.write(f"**Bonus Auto Rich dibayarkan:** Rp{res['bonus_rich']:,.0f}")
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
