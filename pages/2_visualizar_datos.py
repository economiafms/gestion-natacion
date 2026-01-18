# --- TAB 2: FICHA DEL NADADOR ---
with tab2:
    df_t = data['tiempos'].copy()
    df_t = df_t.merge(data['estilos'], on='codestilo', how='left').merge(data['distancias'], on='coddistancia', how='left').merge(data['piletas'], on='codpileta', how='left')
    df_t['Sede_Full'] = df_t['club'].astype(str) + " (" + df_t['medida'].astype(str) + ")"
    df_t = df_t.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
    
    f_nad = st.selectbox("Seleccione un Nadador:", sorted(df_nad['Nombre Completo'].unique().tolist()), index=None)
    
    if f_nad:
        # 1. Obtención de datos básicos del nadador
        info_nadador = df_nad[df_nad['Nombre Completo'] == f_nad].iloc[0]
        id_actual = info_nadador['codnadador']
        fecha_nac_dt = pd.to_datetime(info_nadador['fechanac'])
        
        # Cálculo de Edad y Categoría (Regla 31/12)
        anio_actual = 2025 # O usar datetime.now().year
        edad_master = anio_actual - fecha_nac_dt.year
        
        def obtener_categoria_texto(edad):
            for _, r in data['categorias'].iterrows():
                if r['edad_min'] <= edad <= r['edad_max']: return r['nombre_cat']
            return "S/C"
        
        categoria_actual = obtener_categoria_texto(edad_master)

        # --- CABECERA DE DATOS PERSONALES ---
        st.header(f"👤 {info_nadador['apellido'].upper()}, {info_nadador['nombre']}")
        
        c_info1, c_info2, c_info3, c_info4 = st.columns(4)
        c_info1.markdown(f"**Nacimiento:** \n{fecha_nac_dt.strftime('%d/%m/%Y')}")
        c_info2.markdown(f"**Edad (al 31/12):** \n{edad_master} años")
        c_info3.markdown(f"**Categoría:** \n{categoria_actual}")
        c_info4.markdown(f"**Género:** \n{info_nadador['codgenero']}")
        
        st.divider()

        # --- MEDALLERO (Mantenemos tu lógica) ---
        pos_ind = df_t[df_t['codnadador'] == id_actual]['posicion'].value_counts()
        df_r_base = data['relevos'].copy()
        cond_rel = (df_r_base['nadador_1'] == id_actual) | (df_r_base['nadador_2'] == id_actual) | \
                   (df_r_base['nadador_3'] == id_actual) | (df_r_base['nadador_4'] == id_actual)
        pos_rel = df_r_base[cond_rel]['posicion'].value_counts()
        oro, plata, bronce = pos_ind.get(1,0)+pos_rel.get(1,0), pos_ind.get(2,0)+pos_rel.get(2,0), pos_ind.get(3,0)+pos_rel.get(3,0)
        
        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
        c_m1.metric("🥇 Oros", int(oro))
        c_m2.metric("🥈 Platas", int(plata))
        c_m3.metric("🥉 Bronces", int(bronce))
        c_m4.metric("📊 Total Podios", int(oro+plata+bronce))

        st.divider()

        # --- MEJORES MARCAS (TARJETAS - Mantenemos tu lógica) ---
        st.subheader("✨ Mejores Marcas Personales")
        mis_tiempos = df_t[df_t['codnadador'] == id_actual].copy()
        if not mis_tiempos.empty:
            mis_tiempos['segundos'] = mis_tiempos['tiempo'].apply(tiempo_a_segundos)
            idx_pb = mis_tiempos.groupby(['Estilo', 'Distancia'])['segundos'].idxmin()
            df_pb = mis_tiempos.loc[idx_pb].sort_values('metros_totales')
            est_disp = [e for e in ['Mariposa', 'Espalda', 'Pecho', 'Crol', 'Combinado'] if e in df_pb['Estilo'].unique()]
            cols_est = st.columns(len(est_disp))
            for i, estilo in enumerate(est_disp):
                with cols_est[i]:
                    st.write(f"**{estilo}**")
                    df_e = df_pb[df_pb['Estilo'] == estilo]
                    for _, row in df_e.iterrows():
                        st.caption(f"{row['Distancia']}"); st.code(row['tiempo'], language=None)
        
        st.divider()

        # --- HISTORIAL INDIVIDUAL (FILTROS COMUNICADOS - Mantenemos tu lógica) ---
        st.subheader("📜 Historial Individual")
        
        c1, c2 = st.columns(2)
        h_est_sel = c1.selectbox("Filtrar por Estilo:", ["Todos"] + sorted(mis_tiempos['Estilo'].unique().tolist()), key="h_ind_est")
        
        df_temp_dis = mis_tiempos.copy()
        if h_est_sel != "Todos":
            df_temp_dis = df_temp_dis[df_temp_dis['Estilo'] == h_est_sel]
        
        h_dis_sel = c2.selectbox("Filtrar por Distancia:", ["Todos"] + sorted(df_temp_dis['Distancia'].unique().tolist()), key="h_ind_dis")
        
        df_hist = df_temp_dis.copy()
        if h_dis_sel != "Todos":
            df_hist = df_hist[df_hist['Distancia'] == h_dis_sel]
        
        st.dataframe(df_hist[['fecha', 'Estilo', 'Distancia', 'tiempo', 'posicion', 'Sede_Full']].sort_values('fecha', ascending=False), use_container_width=True, hide_index=True)

        st.divider()

       # --- MIS RELEVOS (SIN DISTANCIA) ---
        st.subheader("🏊‍♂️ Mis Relevos")
        mis_r = df_r_base[cond_rel].copy()
        if not mis_r.empty:
            mis_r = mis_r.merge(data['estilos'], on='codestilo', how='left').merge(data['distancias'], on='coddistancia', how='left').merge(data['piletas'], on='codpileta', how='left')
            mis_r['Sede_Full'] = mis_r['club'].astype(str) + " (" + mis_r['medida'].astype(str) + ")"
            mis_r = mis_r.rename(columns={'descripcion_x': 'Estilo', 'descripcion_y': 'Distancia'})
            
            cr1, cr2 = st.columns(2)
            # Filtro 1: Estilo
            fr_est_sel = cr1.selectbox("Estilo Relevo:", ["Todos"] + sorted(mis_r['Estilo'].unique().tolist()), key="fr_rel_est")
            
            df_rel_temp = mis_r.copy()
            if fr_est_sel != "Todos":
                df_rel_temp = df_rel_temp[df_rel_temp['Estilo'] == fr_est_sel]
            
            # Filtro 2: Género (Dependiente del Estilo)
            fr_gen_sel = cr2.selectbox("Género Relevo:", ["Todos"] + sorted(df_rel_temp['codgenero'].unique().tolist()), key="fr_rel_gen")
            
            if fr_gen_sel != "Todos":
                df_rel_temp = df_rel_temp[df_rel_temp['codgenero'] == fr_gen_sel]

            def obtener_equipo_pro(row):
                detalles = []
                for i in range(1, 5):
                    nom = dict_id_nombre.get(row[f'nadador_{i}'], "?")
                    t = str(row[f'tiempo_{i}']).strip()
                    if t and t not in ["00.00", "00:00.00", "0", "None", "nan"]:
                        detalles.append(f"{nom} ({t})")
                    else:
                        detalles.append(nom)
                return " / ".join(detalles)
            
            df_rel_temp['Equipo y Marcas'] = df_rel_temp.apply(obtener_equipo_pro, axis=1)
            
            # Tabla final sin la columna Distancia
            st.dataframe(df_rel_temp[['fecha', 'Estilo', 'codgenero', 'tiempo_final', 'posicion', 'Sede_Full', 'Equipo y Marcas']].sort_values('fecha', ascending=False),
                         use_container_width=True, hide_index=True)
