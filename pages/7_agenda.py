# === A. LISTA PÚBLICA DE INSCRIPTOS (CON CHIPS REPLICANDO DISEÑO DE IMAGEN) ===
with st.expander("📋 Ver Lista de Inscriptos"):
    f_ins = df_inscripciones[df_inscripciones['id_competencia'] == comp_id]
    if f_ins.empty:
        st.caption("Aún no hay nadadores inscriptos.")
    else:
        d_full = f_ins.merge(df_nadadores, on="codnadador", how="left")
        d_full['Anio'] = d_full['fechanac'].dt.year
        d_full['Cat'] = d_full['Anio'].apply(calcular_categoria_master)
        
        for _, r_pub in d_full.iterrows():
            nadador_nom = f"{r_pub['apellido']}, {r_pub['nombre']}"
            
            # Chips para las pruebas (Estilos)
            pruebas_lista = [p.strip() for p in str(r_pub['pruebas']).split(",")]
            chips_html = "".join([f"<span style='background-color:#333; color:#aaa; padding:3px 8px; border-radius:4px; font-size:11px; margin-right:5px; display:inline-block; border:1px solid #444;'>{p}</span>" for p in pruebas_lista])

            st.markdown(f"""
            <div style="
                background-color: #262730; 
                padding: 12px; 
                border-radius: 8px; 
                margin-bottom: 8px; 
                border-left: 4px solid #E30613;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border: 1px solid #333;">
                
                <div style="flex-grow: 1;">
                    <div style="font-weight: bold; color: white; font-size: 16px; margin-bottom: 8px;">{nadador_nom}</div>
                    <div style="display: flex; flex-wrap: wrap; gap: 4px;">{chips_html}</div>
                </div>
                
                <div style="display: flex; flex-direction: column; align-items: flex-end; min-width: 100px;">
                    <div style="
                        font-size: 16px; 
                        font-weight: bold; 
                        background-color: #444; 
                        padding: 5px 12px; 
                        border-radius: 6px; 
                        color: #fff;
                        margin-bottom: 5px;
                        text-align: center;
                        width: fit-content;">
                        {r_pub['Cat']}
                    </div>
                    <div style="
                        font-size: 12px; 
                        font-weight: bold; 
                        background-color: #333; 
                        padding: 3px 10px; 
                        border-radius: 4px; 
                        color: #ccc;
                        border: 1px solid #444;">
                        Gen. {r_pub['codgenero']}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
