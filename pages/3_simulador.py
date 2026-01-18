# --- MÓDULO 1: SIMULADOR MANUAL CON DESGLOSE DE PARCIALES ---
st.divider()
st.subheader("🧪 Simulación de Equipo y Estrategia")

with st.container(border=True):
    # (Selectores de Reglamento, Estilo y Género se mantienen igual)
    # ... 
    
    if st.button("🚀 Calcular Estrategia y Parciales", use_container_width=True):
        if len(set(n_sel)) == 4 and None not in n_sel:
            # 1. Obtención de Marcas Individuales de 50m
            detalles_sim = []
            id_est_sim = data['estilos'][data['estilos']['descripcion'] == s_est]['codestilo'].values[0]
            
            for nad in n_sel:
                id_n = df_nad[df_nad['Nombre Completo'] == nad]['codnadador'].values[0]
                t_seg = obtener_mejor_50m(id_n, id_est_sim)
                detalles_sim.append({'nombre': nad, 'parcial': t_seg})
            
            t_total_sim = sum([d['parcial'] for d in detalles_sim])

            # 2. Análisis de Eficiencia (Sugerencia de Orden)
            # Regla: En Crol, el más rápido suele ir al final (Cierre)
            sugerencia = sorted(detalles_sim, key=lambda x: x['parcial'], reverse=True)
            
            # 3. Mostrar Resultados y Parciales
            st.write("### 📋 Desglose de la Simulación (4x50m)")
            cols_p = st.columns(4)
            for i, d in enumerate(detalles_sim):
                cols_p[i].metric(f"P{i+1}: {d['nombre'].split(',')[1]}", segundos_a_tiempo(d['parcial']))
            
            st.success(f"**Tiempo Total Simulado: {segundos_a_tiempo(t_total_sim)}**")

            # 4. Comparación con Antecedente Histórico Real
            ids_actuales = sorted([df_nad[df_nad['Nombre Completo'] == n]['codnadador'].values[0] for n in n_sel])
            def es_el_mismo_equipo(row):
                return sorted([row['nadador_1'], row['nadador_2'], row['nadador_3'], row['nadador_4']]) == ids_actuales
            
            antecedente = data['relevos'][data['relevos'].apply(es_el_mismo_equipo, axis=1)]

            if not antecedente.empty:
                ant = antecedente.sort_values('tiempo_final').iloc[0]
                st.write("---")
                st.write(f"### 📜 Registro Histórico Encontrado ({ant['fecha']})")
                
                # Mostramos los parciales que se grabaron en ese momento
                res_ant = st.columns(4)
                for i in range(1, 5):
                    nom_ant = dict_id_nombre.get(ant[f'nadador_{i}'], "Desconocido")
                    t_ant = ant[f'tiempo_{i}']
                    res_ant[i-1].write(f"**Pos {i}:** {nom_ant}")
                    res_ant[i-1].code(t_ant)
                
                st.warning(f"**Tiempo Real en Torneo: {ant['tiempo_final']}**")
                
                # Comparación técnica
                dif = t_total_sim - tiempo_a_segundos(ant['tiempo_final'])
                if dif < 0:
                    st.write(f"💡 El equipo está simulando **{abs(dif):.2f}s más rápido** que su mejor marca histórica.")
                else:
                    st.write(f"⚠️ El equipo está simulando **{dif:.2f}s por debajo** de su récord conjunto.")

            # 5. Sugerencia Proactiva
            with st.expander("💡 Sugerencia de Orden Eficiente"):
                st.write("Para maximizar el rendimiento, el orden sugerido basado en marcas actuales es:")
                for i, s in enumerate(sugerencia):
                    st.write(f"{i+1}. {s['nombre']} ({segundos_a_tiempo(s['parcial'])})")
