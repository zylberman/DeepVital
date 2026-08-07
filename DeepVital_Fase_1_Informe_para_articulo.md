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
interno. Cada paciente se asigna a un solo fold externo, todas sus ventanas se
mantienen juntas y cada ventana elegible recibe exactamente una predicción OOF. Esta evaluación
se denomina `internal_nested_cross_validation`, no validación externa.

La ejecución canónica actual incluyó 8.970 ventanas de 92 pacientes con ventanas
elegibles. Los benchmarks clínicos y la estrategia ML usaron los mismos folds y
ventanas. La media de MAP de las seis horas previas obtuvo AUPRC 0,6219, frente a
0,5333 para la estrategia ML anidada; la última MAP obtuvo 0,5613. Esto es una
comparación de desarrollo y no selecciona todavía un modelo definitivo.

Cada fold externo conserva el threshold derivado exclusivamente de sus folds
internos. Las métricas pooled a threshold 0,5 son descriptivas. Todavía no existe
un único threshold final congelado; se estimará con predicciones out-of-fold de
todos los datos de desarrollo sólo después de elegir la estrategia de modelo.

Las transformaciones clínicas sigmoidales se consideran scores de ranking no
calibrados; para ellas no se reportan Brier ni log loss. La estrategia principal
asigna 0,5 cuando un score no es calculable y se acompaña de sensibilidad
complete-case y conteos agregados de disponibilidad.

La comparación pareada remuestreó pacientes y conservó todas sus ventanas. Para la
media de MAP de seis horas frente a la estrategia ML, delta AUPRC fue 0,0886
(IC95% pareado 0,0205–0,1453) y delta AUROC 0,0231 (0,0010–0,0419). Estas cifras de
desarrollo no constituyen por sí solas selección definitiva ni superioridad clínica.

## Evaluación confirmatoria y externa futuras

No existe actualmente un test confirmatorio. Todos los 100 pacientes disponibles
son datos de desarrollo. Una evaluación confirmatoria futura exige pacientes
completamente nuevos, protocolo, cohorte, modelo y threshold congelados. La
validación externa requerirá además un entorno o fuente de datos independiente.

Las definiciones completas están en `docs/EVALUATION_PROTOCOL.md`, la decisión de
cohorte en `docs/PHASE_1B_COHORT_DECISION.md` y el incidente histórico en
`docs/HOLDOUT_REUSE_ASSESSMENT.md`.
