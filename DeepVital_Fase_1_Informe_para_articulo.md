# DeepVital: estado de Fase 1 y transición al protocolo reparado

DeepVital es un prototipo retrospectivo de investigación y no un dispositivo
médico. No debe utilizarse para decisiones clínicas.

## Resultados históricos de desarrollo

La construcción histórica de Fase 1B produjo 12.309 filas horarias y 8.872 ventanas
(1.759 positivas; prevalencia 19,83%). Estos datos sustentan los resultados de Fase
2 previamente publicados en el repositorio. El antiguo test se denomina ahora
`development_holdout_v1`: fue accedido cuatro veces y no es un holdout confirmatorio
intacto. Sus métricas no se han modificado ni eliminado.

## Cohorte canónica

La cohorte canónica utiliza los límites administrativos FHIR de cada estancia de
UCI. Su construcción registrada produce 12.502 filas horarias y 8.970 ventanas
(1.774 positivas; prevalencia 19,78%). Esta diferencia procede de representar todo
el periodo clínico de riesgo y excluir 270 observaciones fuera de sus límites, no de
optimizar métricas.

## Validación interna

La evaluación interna prevista es validación cruzada anidada agrupada por paciente.
Modelo, hiperparámetros y threshold se seleccionan exclusivamente dentro del ciclo
interno. Cada paciente recibe predicciones externas una sola vez. Esta evaluación
se denomina `internal_nested_cross_validation`, no validación externa.

La ejecución canónica actual incluyó 8.970 ventanas de 92 pacientes con ventanas
elegibles. Las métricas pooled descriptivas fueron AUROC 0,8185, AUPRC 0,5333 y
Brier 0,1354. El bootstrap agrupado por paciente produjo intervalos percentiles del
95% de 0,7747–0,8633 para AUROC, 0,4226–0,6423 para AUPRC y 0,1092–0,1605 para
Brier. Estos resultados son internos y no sustentan generalización clínica.

## Evaluación confirmatoria y externa futuras

No existe actualmente un test confirmatorio. Todos los 100 pacientes disponibles
son datos de desarrollo. Una evaluación confirmatoria futura exige pacientes
completamente nuevos, protocolo, cohorte, modelo y threshold congelados. La
validación externa requerirá además un entorno o fuente de datos independiente.

Las definiciones completas están en `docs/EVALUATION_PROTOCOL.md`, la decisión de
cohorte en `docs/PHASE_1B_COHORT_DECISION.md` y el incidente histórico en
`docs/HOLDOUT_REUSE_ASSESSMENT.md`.
