import streamlit as st
from collections import deque
import pandas as pd
import random

# ---------------------------- Data Model ----------------------------
class Member:
    def __init__(self, id, name, sponsor_id, parent_id=None, is_active=False):
        self.id = id
        self.name = name
        self.sponsor_id = sponsor_id          # untuk Auto Rich (parent langsung)
        self.parent_id = parent_id            # untuk Auto Cuan (placement tree)
        self.left_child_id = None
        self.right_child_id = None
        self.is_active = is_active            # status Auto Cuan bulan ini
        self.balance_cuan = 0
        self.balance_rich = 0
        self.total_spent = 0                  # total belanja (simulasi)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'sponsor_id': self.sponsor_id,
            'parent_id': self.parent_id,
            'left_child_id': self.left_child_id,
            'right_child_id': self.right_child_id,
            'is_active': self.is_active,
            'balance_cuan': self.balance_cuan,
            'balance_rich': self.balance_rich,
            'total_spent': self.total_spent
        }

# ---------------------------- Helper Functions ----------------------------
def init_session():
    if 'members' not in st.session_state:
        # Member root (Perusahaan) dengan id=1
        root = Member(1, "Perusahaan", sponsor_id=None, parent_id=None, is_active=True)
        st.session_state.members = {1: root}
        st.session_state.next_id = 2
        st.session_state.total_cash_in = 0
        st.session_state.total_bonus_cuan = 0
        st.session_state.total_bonus_rich = 0

def find_placement_cuan(sponsor_id, members):
    """
    Mencari posisi kosong untuk member baru di Auto Cuan (binary tree, prioritas kanan).
    Kembalikan (parent_id, is_left) dimana is_left = True untuk anak kiri, False untuk kanan.
    """
    root_id = sponsor_id
    # BFS dengan prioritas kanan (masukkan right child dulu ke queue)
    queue = deque([root_id])
    while queue:
        node_id = queue.popleft()
        node = members[node_id]
        # Prioritas kanan: cek slot kanan dulu
        if node.right_child_id is None:
            return (node_id, False)
        if node.left_child_id is None:
            return (node_id, True)
        # Jika kedua slot penuh, tambahkan anak dengan urutan kanan dulu, lalu kiri
        if node.right_child_id:
            queue.append(node.right_child_id)
        if node.left_child_id:
            queue.append(node.left_child_id)
    # Seharusnya tidak terjadi karena pasti ada slot di pohon tak terbatas
    return (sponsor_id, True)

def register_member(sponsor_id, name):
    """Registrasi member baru dengan sponsor tertentu."""
    members = st.session_state.members
    if sponsor_id not in members:
        return None
    
    new_id = st.session_state.next_id
    st.session_state.next_id += 1
    
    # Tentukan parent untuk Auto Cuan (placement)
    parent_id, is_left = find_placement_cuan(sponsor_id, members)
    
    # Buat member baru (default tidak aktif)
    new_member = Member(new_id, name, sponsor_id, parent_id, is_active=False)
    
    # Simpan ke dictionary
    members[new_id] = new_member
    
    # Update hubungan di parent
    parent = members[parent_id]
    if not is_left:
        parent.right_child_id = new_id
    else:
        parent.left_child_id = new_id
    
    return new_member

def get_ancestors_cuan(member_id, members, max_level=7):
    """
    Mengembalikan list ancestor (dari level 1 hingga max_level) di placement tree.
    Setiap elemen: (id, level)
    Level 1 = parent langsung, level 2 = parentnya parent, dst.
    """
    ancestors = []
    current_id = members[member_id].parent_id
    level = 1
    while current_id is not None and level <= max_level:
        ancestors.append((current_id, level))
        current_id = members[current_id].parent_id
        level += 1
    return ancestors

def get_ancestors_rich(member_id, members, max_level=7):
    """Untuk Auto Rich: ancestor berdasarkan sponsor tree (sponsor_id)."""
    ancestors = []
    current_id = members[member_id].sponsor_id
    level = 1
    while current_id is not None and level <= max_level:
        ancestors.append((current_id, level))
        current_id = members[current_id].sponsor_id
        level += 1
    return ancestors

def process_transaction(member_id, amount):
    """
    Memproses transaksi belanja member.
    amount: nominal belanja (minimal 100000 untuk aktif? tapi di Auto Rich tidak ada syarat)
    Namun untuk Auto Cuan, jika member aktif (is_active True) maka komisi matrix dibayar.
    Status aktif member ditentukan dari apakah member sudah bayar minimal 100k bulan ini.
    Di simulasi, kita asumsikan jika amount >= 100000 maka member menjadi aktif bulan ini.
    """
    members = st.session_state.members
    if member_id not in members:
        return None
    
    member = members[member_id]
    # Update status aktif berdasarkan belanja (minimal 100rb)
    if amount >= 100000:
        member.is_active = True
    else:
        member.is_active = False  # jika kurang, tidak aktif
    
    member.total_spent += amount
    st.session_state.total_cash_in += amount
    
    # -------------------- Hitung Komisi Auto Cuan --------------------
    # Syarat: member pembayar harus aktif? Dari dokumen: pembayar harus aktif agar komisi mengalir?
    # Di Auto Cuan, komisi dibayar jika pembayar aktif dan semua ancestor di jalur aktif.
    # Jika pembayar tidak aktif, tidak ada komisi matrix.
    bonus_cuan = 0
    if member.is_active:
        ancestors = get_ancestors_cuan(member_id, members, max_level=7)
        # Periksa rantai aktif dari bawah ke atas
        valid_ancestors = []
        for anc_id, level in ancestors:
            if members[anc_id].is_active:
                valid_ancestors.append((anc_id, level))
            else:
                break  # berhenti jika ada yang tidak aktif
        n = len(valid_ancestors)
        if n > 0:
            # Level 1 sampai n-1 dapat Rp4000, level n (tertinggi) dapat Rp9000
            for i, (anc_id, level) in enumerate(valid_ancestors):
                if i == n-1:  # last ancestor
                    komisi = 9000
                else:
                    komisi = 4000
                members[anc_id].balance_cuan += komisi
                bonus_cuan += komisi
                st.session_state.total_bonus_cuan += komisi
    
    # Bonus sponsor (Rp1000) untuk sponsor langsung pembayar
    sponsor_id = member.sponsor_id
    if sponsor_id is not None and sponsor_id in members:
        sponsor = members[sponsor_id]
        sponsor.balance_cuan += 1000
        bonus_cuan += 1000
        st.session_state.total_bonus_cuan += 1000
    
    # -------------------- Hitung Komisi Auto Rich (flat Rp5000 per ancestor, tanpa syarat) --------------------
    bonus_rich = 0
    ancestors_rich = get_ancestors_rich(member_id, members, max_level=7)
    for anc_id, level in ancestors_rich:
        members[anc_id].balance_rich += 5000
        bonus_rich += 5000
        st.session_state.total_bonus_rich += 5000
    
    total_bonus = bonus_cuan + bonus_rich
    return {
        'amount': amount,
        'member_active': member.is_active,
        'bonus_cuan': bonus_cuan,
        'bonus_rich': bonus_rich,
        'total_bonus': total_bonus,
        'ancestors_cuan': [a[0] for a in get_ancestors_cuan(member_id, members)],
        'ancestors_rich': [a[0] for a in ancestors_rich]
    }

def get_member_tree_cuan(root_id, members):
    """Membangun struktur pohon binary untuk visualisasi Graphviz (Auto Cuan)."""
    if root_id not in members:
        return ""
    lines = []
    queue = deque([root_id])
    while queue:
        node_id = queue.popleft()
        node = members[node_id]
        label = f"{node.name} (ID:{node.id})\n{'Aktif' if node.is_active else 'Tdk Aktif'}"
        lines.append(f'    "{node_id}" [label="{label}"];')
        if node.left_child_id:
            lines.append(f'    "{node_id}" -> "{node.left_child_id}";')
            queue.append(node.left_child_id)
        if node.right_child_id:
            lines.append(f'    "{node_id}" -> "{node.right_child_id}";')
            queue.append(node.right_child_id)
    return "digraph G {\n" + "\n".join(lines) + "\n}"

def get_member_tree_rich(root_id, members):
    """Struktur pohon tak terbatas untuk Auto Rich (berdasarkan sponsor)."""
    # Kita buat adjacency dari semua member berdasarkan sponsor_id
    if root_id not in members:
        return ""
    lines = []
    # Kumpulkan semua node
    all_ids = list(members.keys())
    for mid in all_ids:
        node = members[mid]
        label = f"{node.name} (ID:{node.id})\n{node.balance_rich:,}"
        lines.append(f'    "{mid}" [label="{label}"];')
    for mid in all_ids:
        sponsor = members[mid].sponsor_id
        if sponsor is not None and sponsor in members:
            lines.append(f'    "{sponsor}" -> "{mid}";')
    return "digraph G {\n" + "\n".join(lines) + "\n}"

# ---------------------------- UI Streamlit ----------------------------
def main():
    st.set_page_config(page_title="K-BBPT Network Simulator", layout="wide")
    st.title("K-BBPT Simulator Jaringan & Komisi")
    st.markdown("Simulasi Auto Cuan (Binary + Spillover Prioritas Kanan) dan Auto Rich (Unlimited Direct)")
    
    init_session()
    
    # Sidebar untuk navigasi
    menu = st.sidebar.selectbox("Menu", ["Dashboard", "Registrasi Member", "Simulasi Transaksi", "Visualisasi Jaringan"])
    
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
        
        st.subheader("📋 Daftar Member")
        df_data = []
        for m in members.values():
            df_data.append({
                "ID": m.id,
                "Nama": m.name,
                "Sponsor ID": m.sponsor_id,
                "Parent Cuan": m.parent_id,
                "Status Aktif": "✅ Aktif" if m.is_active else "❌ Tidak Aktif",
                "Balance Cuan": m.balance_cuan,
                "Balance Rich": m.balance_rich,
                "Total Belanja": m.total_spent
            })
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
    
    elif menu == "Registrasi Member":
        st.header("📝 Registrasi Member Baru")
        with st.form("register_form"):
            name = st.text_input("Nama Lengkap")
            sponsor_options = {m.id: f"{m.name} (ID:{m.id})" for m in members.values()}
            sponsor_id = st.selectbox("Pilih Sponsor", options=list(sponsor_options.keys()), format_func=lambda x: sponsor_options[x])
            submitted = st.form_submit_button("Daftarkan")
            if submitted:
                if not name.strip():
                    st.error("Nama tidak boleh kosong")
                else:
                    new_member = register_member(sponsor_id, name.strip())
                    if new_member:
                        st.success(f"Member {new_member.name} (ID:{new_member.id}) berhasil didaftarkan!")
                        # Tampilkan posisi placement
                        parent = members[new_member.parent_id]
                        pos = "kanan" if parent.right_child_id == new_member.id else "kiri"
                        st.info(f"Auto Cuan: ditempatkan sebagai anak {pos} dari {parent.name} (ID:{parent.id})")
                        st.info(f"Auto Rich: sponsor langsung adalah {members[sponsor_id].name}")
                    else:
                        st.error("Sponsor tidak valid")
    
    elif menu == "Simulasi Transaksi":
        st.header("💰 Simulasi Belanja & Komisi")
        member_options = {m.id: f"{m.name} (ID:{m.id})" for m in members.values()}
        member_id = st.selectbox("Pilih member yang melakukan transaksi", options=list(member_options.keys()), format_func=lambda x: member_options[x])
        amount = st.number_input("Nominal Belanja (Rp)", min_value=0, step=10000, value=100000)
        if st.button("Proses Transaksi"):
            if member_id in members:
                result = process_transaction(member_id, amount)
                if result:
                    st.success(f"Transaksi Rp{amount:,.0f} oleh {members[member_id].name}")
                    st.write(f"**Status Auto Cuan member:** {'Aktif' if result['member_active'] else 'Tidak Aktif (komisi matrix tidak dibayar)'}")
                    st.write(f"**Bonus Auto Cuan yang dibayarkan:** Rp{result['bonus_cuan']:,.0f}")
                    st.write(f"**Bonus Auto Rich yang dibayarkan:** Rp{result['bonus_rich']:,.0f}")
                    st.write(f"**Total Komisi:** Rp{result['total_bonus']:,.0f}")
                    st.write(f"**Ancestor Cuan (placement):** {result['ancestors_cuan'] if result['ancestors_cuan'] else 'Tidak ada'}")
                    st.write(f"**Ancestor Rich (sponsor):** {result['ancestors_rich'] if result['ancestors_rich'] else 'Tidak ada'}")
                else:
                    st.error("Member tidak ditemukan")
            else:
                st.error("Member tidak valid")
    
    elif menu == "Visualisasi Jaringan":
        st.header("🌳 Visualisasi Jaringan")
        network_type = st.radio("Pilih jenis jaringan", ["Auto Cuan (Binary / Placement)", "Auto Rich (Sponsor Tree)"])
        root_options = {m.id: f"{m.name} (ID:{m.id})" for m in members.values()}
        root_id = st.selectbox("Root / Member awal", options=list(root_options.keys()), format_func=lambda x: root_options[x])
        if network_type == "Auto Cuan (Binary / Placement)":
            dot = get_member_tree_cuan(root_id, members)
        else:
            dot = get_member_tree_rich(root_id, members)
        if dot:
            st.graphviz_chart(dot)
        else:
            st.warning("Pohon kosong atau root tidak ditemukan")

if __name__ == "__main__":
    main()
