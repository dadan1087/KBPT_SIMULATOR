# Di dalam tab4 (Visualisasi), ganti dengan:

    with tab4:
        st.header("🌳 Visualisasi Jaringan")
        net_type = st.radio("Pilih jenis jaringan", ["Auto Cuan (Binary / Placement)", "Auto Rich (Sponsor Tree)"])
        root_options = {m.id: f"{m.name} (ID:{m.id})" for m in st.session_state.members.values()}
        root_id = st.selectbox("Root / Member awal", options=list(root_options.keys()), format_func=lambda x: root_options[x])
        
        search_term = st.text_input("🔍 Cari member (nama atau ID)", placeholder="Contoh: Member 1 atau ID 5")
        search_id = None
        if search_term:
            search_term_lower = search_term.lower()
            for m in st.session_state.members.values():
                if search_term_lower == m.name.lower() or search_term == str(m.id):
                    search_id = m.id
                    break
            if search_id is None:
                st.warning("Member tidak ditemukan.")
        
        if net_type == "Auto Cuan (Binary / Placement)":
            dot = get_member_tree_cuan(root_id, st.session_state.members, search_id)
        else:
            dot = get_member_tree_rich(root_id, st.session_state.members, search_id)
        
        if dot:
            st.graphviz_chart(dot)
            st.caption("💡 Tips: Gunakan Ctrl + Scroll pada area grafik untuk zoom. Klik kanan untuk menyimpan gambar.")
        else:
            st.warning("Pohon kosong atau root tidak ditemukan.")
