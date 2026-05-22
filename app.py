import streamlit as st
from collections import deque
import pandas as pd

# ---------------------------- Data Model ----------------------------
class Member:
    def __init__(self, id, name, sponsor_id, parent_id=None, is_active=True):
        self.id = id
        self.name = name
        self.sponsor_id = sponsor_id
        self.parent_id = parent_id
        self.left_child_id = None
        self.right_child_id = None
        self.is_active = is_active
        self.balance_cuan = 0
        self.balance_rich = 0
        self.total_spent = 0
    
    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'sponsor_id': self.sponsor_id,
            'parent_id': self.parent_id, 'left_child_id': self.left_child_id,
            'right_child_id': self.right_child_id, 'is_active': self.is_active,
            'balance_cuan': self.balance_cuan, 'balance_rich': self.balance_rich,
            'total_spent': self.total_spent
        }

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
    root_id = sponsor_id
    queue = deque([root_id])
    while queue:
        node_id = queue.popleft()
        node = members[node_id]
        if node.right_child_id is None:
            return (node_id, False)
        if node.left_child_id is None:
            return (node_id, True)
        if node.right_child_id:
            queue.append(node.right_child_id)
        if node.left_child_id:
            queue.append(node.left_child_id)
    return (sponsor_id, True)

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
    current_id = members[member_id].parent_id
    level = 1
    while current_id is not None and level <= max_level:
        ancestors.append((current_id, level))
        current_id = members[current_id].parent_id
        level += 1
    return ancestors

def get_ancestors_rich(member_id, members, max_level=7):
    ancestors = []
    current_id = members[member_id].sponsor_id
    level = 1
    while current_id is not None and level <= max_level:
        ancestors.append((current_id, level))
        current_id = members[current_id].sponsor_id
        level += 1
    return ancestors

def calculate_commission_preview(member_id, amount, members):
    """Menghitung komisi tanpa menyimpan ke saldo, untuk preview di dashboard."""
    if member_id not in members:
        return None
    member = members[member_id]
    # Status aktif sementara untuk perhitungan (berdasarkan belanja)
    is_active_temp = (amount >= 100000)
    
    result = {
        'payer_id': member_id,
        'payer_name': member.name,
        'amount': amount,
        'payer_active': is_active_temp,
        'cuan_commissions': [],
        'rich_commissions': [],
        'total_cuan': 0,
        'total_rich': 0
    }
    
    # Auto Cuan Matrix (jika aktif)
    if is_active_temp:
        ancestors = get_ancestors_cuan(member_id, members, max_level=7)
        valid_ancestors = []
        for anc_id, level in ancestors:
            if members[anc_id].is_active:
                valid_ancestors.append((anc_id, level))
            else:
                break
        n = len(valid_ancestors)
        for i, (anc_id, level) in enumerate(valid_ancestors):
            komisi = 9000 if i == n-1 else 4000
            result['cuan_commissions'].append({
                'member_id': anc_id,
                'member_name': members[anc_id].name,
                'level': level,
                'type': 'Matrix (Last)' if i == n-1 else 'Matrix',
                'amount': komisi
            })
            result['total_cuan'] += komisi
    
    # Bonus Sponsor
    sponsor_id = member.sponsor_id
    if sponsor_id and sponsor_id in members:
        result['cuan_commissions'].append({
            'member_id': sponsor_id,
            'member_name': members[sponsor_id].name,
            'level': 0,  # bukan level matrix
            'type': 'Bonus Sponsor',
            'amount': 1000
        })
        result['total_cuan'] += 1000
    
    # Auto Rich (flat 5000 per ancestor tanpa syarat)
    ancestors_rich = get_ancestors_rich(member_id, members, max_level=7)
    for anc_id, level in ancestors_rich:
        result['rich_commissions'].append({
            'member_id': anc_id,
            'member_name': members[anc_id].name,
            'level': level,
            'amount': 5000
        })
        result['total_rich'] += 5000
    
    return result

def process_transaction(member_id, amount):
    members = st.session_state.members
    if member_id not in members:
        return None
    member = members[member_id]
    if amount >= 100000:
        member.is_active = True
    else:
        member.is_active = False
    member.total_spent += amount
    st.session_state.total_cash_in += amount

    bonus_cuan = 0
    if member.is_active:
        ancestors = get_ancestors_cuan(member_id, members, max_level=7)
        valid_ancestors = []
        for anc_id, level in ancestors:
            if members[anc_id].is_active:
                valid_ancestors.append((anc_id, level))
            else:
                break
        n = len(valid_ancestors)
        for i, (anc_id, level) in enumerate(valid_ancestors):
            komisi = 9000 if i == n-1 else 4000
            members[anc_id].balance_cuan += komisi
            bonus_cuan += komisi
            st.session_state.total_bonus_cuan += komisi
    sponsor_id = member.sponsor_id
    if sponsor_id and sponsor_id in members:
        members[sponsor_id].balance_cuan += 1000
        bonus_cuan += 1000
        st.session_state.total_bonus_cuan += 1000

    bonus_rich = 0
    ancestors_rich = get_ancestors_rich(member_id, members, max_level=7)
    for anc_id, level in ancestors_rich:
        members[anc_id].balance_rich += 5000
        bonus_rich += 5000
        st.session_state.total_bonus_rich += 5000

    return {
        'amount': amount,
        'member_active': member.is_active,
        'bonus_cuan': bonus_cuan,
        'bonus_rich': bonus_rich,
        'total_bonus': bonus_cuan + bonus_rich,
        'ancestors_cuan': [a[0] for a in get_ancestors_cuan(member_id, members)],
        'ancestors_rich': [a[0] for a in ancestors_rich]
    }

def get_member_tree_cuan(root_id, members):
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
    if root_id not in members:
        return ""
    lines = []
    for mid, node in members.items():
        label = f"{node.name} (ID:{node.id})\nSaldo: {node.balance_rich:,}"
        lines.append(f'    "{mid}" [label="{label}"];')
    for mid, node in members.items():
        if node.sponsor_id and node.sponsor_id in members:
            lines.append(f'    "{node.sponsor_id}" -> "{mid}";')
    return "digraph G {\n" + "\n".join(lines) + "\n}"

def create_sample_network():
    members = st.session_state.members
    if len(members) > 1:
        st.warning("Jaringan sudah memiliki member. Hapus session state jika ingin membuat ulang.")
        return
    m1 = register_member(1, "Member 1")      # ID2
    m2 = register_member(1, "Member 2")      # ID3
    m3 = register_member(2, "Member 3")      # ID4
    m4 = register_member(2, "Member 4")      # ID5
    m5 = register_member(4, "Member 5")      # ID6
    m6 = register_member(6, "Member 6")      # ID7
    st.success("Jaringan contoh berhasil dibuat!")
    st.info("Struktur placement (Auto Cuan): Perusahaan(1)→kanan: Member1(2)→kanan: Member3(4)→kanan: Member5(6)→kanan: Member6(7)")

# ---------------------------- UI Streamlit ----------------------------
def main():
    st.set_page_config(page_title="K-BBPT Simulator", layout="wide")
    st.title("K-BBPT Simulator Jaringan & Komisi")
    st.markdown("Auto Cuan (Binary + Spillover prioritas kanan) + Auto Rich (Unlimited Direct)")
    
    init_session()
    
    with st.sidebar:
        st.header("Pengaturan")
        if st.button("🔄 Buat Jaringan Contoh"):
            create_sample_network()
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
        
        st.subheader("📋 Daftar Member")
        df_data = []
        for m in members.values():
            df_data.append({
                "ID": m.id, "Nama": m.name, "Sponsor ID": m.sponsor_id,
                "Parent Cuan": m.parent_id, "Status Aktif": "✅" if m.is_active else "❌",
                "Balance Cuan": m.balance_cuan, "Balance Rich": m.balance_rich,
                "Total Belanja": m.total_spent
            })
        st.dataframe(pd.DataFrame(df_data), use_container_width=True)
        
        # ------------------ FITUR BARU: Alur Komisi ------------------
        st.markdown("---")
        st.subheader("🔍 Simulasi Alur Komisi (Preview tanpa menyimpan)")
        st.markdown("Pilih member yang melakukan transaksi, masukkan nominal, dan lihat siapa saja yang mendapat komisi beserta jenisnya.")
        colA, colB = st.columns([1,1])
        with colA:
            member_options = {m.id: f"{m.name} (ID:{m.id})" for m in members.values()}
            selected_member_id = st.selectbox("Member yang bertransaksi", options=list(member_options.keys()), format_func=lambda x: member_options[x], key="preview_member")
        with colB:
            preview_amount = st.number_input("Nominal Belanja (Rp)", min_value=0, step=10000, value=100000, key="preview_amount")
        
        if st.button("Hitung Alur Komisi", key="preview_btn"):
            preview = calculate_commission_preview(selected_member_id, preview_amount, members)
            if preview:
                st.write(f"**Transaksi oleh:** {preview['payer_name']} (ID:{preview['payer_id']})")
                st.write(f"**Nominal:** Rp{preview['amount']:,.0f} → Status Auto Cuan: {'Aktif' if preview['payer_active'] else 'Tidak Aktif'}")
                
                # Tabel Auto Cuan (Matrix + Sponsor)
                if preview['cuan_commissions']:
                    df_cuan = pd.DataFrame(preview['cuan_commissions'])
                    df_cuan = df_cuan.rename(columns={'member_name':'Penerima', 'type':'Jenis', 'level':'Level', 'amount':'Komisi (Rp)'})
                    df_cuan['Komisi (Rp)'] = df_cuan['Komisi (Rp)'].apply(lambda x: f"{x:,.0f}")
                    st.markdown("**Komisi Auto Cuan:**")
                    st.dataframe(df_cuan[['Penerima', 'Jenis', 'Level', 'Komisi (Rp)']], use_container_width=True)
                else:
                    st.info("Tidak ada komisi Auto Cuan (pembayar tidak aktif atau rantai putus).")
                
                # Tabel Auto Rich
                if preview['rich_commissions']:
                    df_rich = pd.DataFrame(preview['rich_commissions'])
                    df_rich = df_rich.rename(columns={'member_name':'Penerima', 'level':'Level (sponsor)', 'amount':'Komisi (Rp)'})
                    df_rich['Komisi (Rp)'] = df_rich['Komisi (Rp)'].apply(lambda x: f"{x:,.0f}")
                    st.markdown("**Komisi Auto Rich (flat Rp5.000 per ancestor):**")
                    st.dataframe(df_rich[['Penerima', 'Level (sponsor)', 'Komisi (Rp)']], use_container_width=True)
                else:
                    st.info("Tidak ada komisi Auto Rich (tidak ada ancestor sponsor).")
                
                st.write(f"**Total Komisi yang akan dibayarkan:** Rp{preview['total_cuan'] + preview['total_rich']:,.0f} (Auto Cuan: Rp{preview['total_cuan']:,.0f}, Auto Rich: Rp{preview['total_rich']:,.0f})")
            else:
                st.error("Member tidak ditemukan.")
    
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
                    new = register_member(sponsor_id, name.strip())
                    if new:
                        st.success(f"Member {new.name} (ID:{new.id}) aktif langsung!")
                        parent = members[new.parent_id]
                        pos = "kanan" if parent.right_child_id == new.id else "kiri"
                        st.info(f"Auto Cuan: anak {pos} dari {parent.name} (ID:{parent.id})")
                        st.info(f"Auto Rich: sponsor = {members[sponsor_id].name}")
                    else:
                        st.error("Sponsor tidak valid")
    
    elif menu == "Simulasi Transaksi":
        st.header("💰 Simulasi Belanja & Komisi (Real, menyimpan ke saldo)")
        member_options = {m.id: f"{m.name} (ID:{m.id})" for m in members.values()}
        member_id = st.selectbox("Pilih member yang transaksi", options=list(member_options.keys()), format_func=lambda x: member_options[x])
        amount = st.number_input("Nominal Belanja (Rp)", min_value=0, step=10000, value=100000)
        if st.button("Proses Transaksi"):
            result = process_transaction(member_id, amount)
            if result:
                st.success(f"Transaksi Rp{amount:,.0f} oleh {members[member_id].name}")
                st.write(f"**Status Auto Cuan member:** {'Aktif' if result['member_active'] else 'Tidak Aktif'}")
                st.write(f"**Bonus Auto Cuan:** Rp{result['bonus_cuan']:,.0f}")
                st.write(f"**Bonus Auto Rich:** Rp{result['bonus_rich']:,.0f}")
                st.write(f"**Total Komisi:** Rp{result['total_bonus']:,.0f}")
                if result['ancestors_cuan']:
                    st.write(f"**Ancestor Cuan (placement):** {result['ancestors_cuan']}")
                else:
                    st.write("**Ancestor Cuan:** Tidak ada")
                st.write(f"**Ancestor Rich (sponsor):** {result['ancestors_rich'] if result['ancestors_rich'] else 'Tidak ada'}")
    
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
