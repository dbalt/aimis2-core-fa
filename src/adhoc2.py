from charset_normalizer.cli import query_yes_no

from libfa2.hier_metadata import Hierarchy, MetricNode, MetricType, Query, ComponentMultiPartType, ComponentRatioPartType
from libfa2.analyt_struct_metadata import AnalyticalStructureMetadata, Algorithm, Dimension



def mk_hier()->Hierarchy:
    h = Hierarchy()

    an_tb = AnalyticalStructureMetadata()
    an_tb.add_algorithm(Algorithm(1, [['tb']]))
    an_tb.add_dimension(Dimension('tb', 'Террбанк', 'tb_name'))

    an_channel = AnalyticalStructureMetadata()
    an_channel.add_algorithm(Algorithm(1, [['channel']]))
    an_channel.add_dimension(Dimension('channel', 'Канал', 'channel'))

    od = MetricNode(
        id = 1,
        code = 'od',
        name = 'ОД до резервов',
        type=MetricType.SUM,
        analyt_metadata=an_channel
    )
    h.add_node(od)


    od_chpd = MetricNode(
        id = 2,
        code = 'od_chpd',
        name = 'Чистый процентный доход',
        type = MetricType.SUM,
        parent=od.id
    )
    h.add_node(od_chpd)

    od_chkd = MetricNode(
        id=3,
        code='od_chkd',
        name='Чистый комиссионный доход',
        query=Query({'code':'R_04'}),
        parent=od.id
    )
    h.add_node(od_chkd)

    od_pchod = MetricNode(
        id=4,
        code='od_pchod',
        name='Прочие чистые операционные доходы',
        type=MetricType.SUM,
        parent=od.id
    )
    h.add_node(od_pchod)



    od_chpd_cash = MetricNode(
        id = 50,
        code = 'od_chpd_cash',
        name = 'Денежные средства',
        parent=od_chpd.id,
        query=Query({'code':'PL_11_31_11'}),
        analyt_metadata=an_tb
    )
    h.add_node(od_chpd_cash)

    od_chpd_preq = MetricNode(
        id=60,
        code='od_chpd_preq',
        name='Основные средства',
        parent=od_chpd.id,
        query=Query({'code': 'R_11_31_14'}),
        analyt_metadata=an_tb
    )
    h.add_node(od_chpd_preq)

    od_chpd_eqtdzo = MetricNode(
        id=70,
        code='od_chpd_eqtdzo',
        name='Фондирование капитала и вложения в ДЗО',
        parent=od_chpd.id,
        query=Query({'code': 'fond_cap_dzo'}),
        analyt_metadata=an_tb
    )
    h.add_node(od_chpd_eqtdzo)



    an_prod_1 = AnalyticalStructureMetadata()
    an_prod_1.add_algorithm(Algorithm(1, [['prod1'], ['prod2'],['prod3']]))
    an_prod_1.add_dimensions([
        Dimension('prod1', 'Продукт ур. 1', 'product_1'),
        Dimension('prod2', 'Продукт ур. 2', 'product_2'),
        Dimension('prod3', 'Продукт ур. 3', 'product_3'),
    ])

    od_pchod_pb = MetricNode(
        id = 80,
        code = 'od_pchod_pb',
        name = 'Продукты банка',
        parent = od_pchod.id,
        type=MetricType.MULTI,
        query=Query({'code':'product_banka'}),
        analyt_metadata=an_prod_1
    )
    h.add_node(od_pchod_pb)



    od_pchod_pb_ratio = MetricNode(
        id = 90,
        code = 'od_pchod_pb_ratio',
        name = 'Тариф',
        parent = od_pchod_pb.id,
        componentMultiPartType=ComponentMultiPartType.RATE
    )
    h.add_node(od_pchod_pb_ratio)


    od_pchod_pb_base = MetricNode(
        id = 100,
        code = 'od_pchod_pb_base',
        name = 'Количество продаж',
        parent = od_pchod_pb.id,
        componentMultiPartType=ComponentMultiPartType.BASE,
        query=Query({'code':'cnt_sales_bsp', 'kpi_name': 'Продукты банка'})
    )
    h.add_node(od_pchod_pb_base)


    od_pchod_ecosys = MetricNode(
        id = 110,
        code = 'od_pchod_ecosys',
        name = 'Экосистема. Доходы небанковского бизнеса',
        parent = od_pchod.id,
        type=MetricType.SUM
    )
    h.add_node(od_pchod_ecosys)


    od_pchod_ecosys_trfrev = MetricNode(
        id = 120,
        code = 'od_pchod_ecosys_trfrev',
        name = 'Тарифная выручка',
        parent = od_pchod_ecosys.id,
        query = Query({'code': 'eco_tar_vyr'}),
        type=MetricType.MULTI,
        analyt_metadata=an_prod_1
    )
    h.add_node(od_pchod_ecosys_trfrev)



    od_pchod_ecosys_trfrev_ratio = MetricNode(
        id = 130,
        code = 'od_pchod_ecosys_trfrev_ratio',
        name = 'Тариф',
        parent = od_pchod_ecosys_trfrev.id,
        componentMultiPartType=ComponentMultiPartType.RATE
    )
    h.add_node(od_pchod_ecosys_trfrev_ratio)


    od_pchod_ecosys_trfrev_base = MetricNode(
        id = 140,
        code = 'od_pchod_ecosys_trfrev_base',
        name = 'Количество продаж',
        parent = od_pchod_ecosys_trfrev.id,
        componentMultiPartType=ComponentMultiPartType.BASE,
        query=Query({'code':'cnt_sales_bsp', 'kpi_name': 'Тарифная выручка'})
    )
    h.add_node(od_pchod_ecosys_trfrev_base)



    od_pchod_ecosys_trfrevdelta = MetricNode(
        id=150,
        code='od_pchod_ecosys_trfrevdelta',
        name='Дельта тарифной выручки и доходных договоров',
        parent=od_pchod_ecosys.id,
        query=Query({'code': 'eco_delta'})
    )
    h.add_node(od_pchod_ecosys_trfrevdelta)



    an_prod_2 = AnalyticalStructureMetadata()
    an_prod_2.add_algorithm(Algorithm(1, [['prod1'], ['prod2'],['prod3'], ['prod4'], ['prod5'], ['prod6'], ['prod7']]))
    an_prod_2.add_dimensions([
        Dimension('prod1', 'Продукт ур. 1', 'product_1'),
        Dimension('prod2', 'Продукт ур. 2', 'product_2'),
        Dimension('prod3', 'Продукт ур. 3', 'product_3'),
        Dimension('prod4', 'Продукт ур. 4', 'product_4'),
        Dimension('prod5', 'Продукт ур. 5', 'product_5'),
        Dimension('prod6', 'Продукт ур. 6', 'product_6'),
        Dimension('prod7', 'Продукт ур. 7', 'product_7'),
    ])


    od_pchod_prub = MetricNode(
        id=160,
        code='od_pchod_prub',
        name='Продукты УБ',
        parent=od_pchod.id,
        type=MetricType.MULTI,
        query=Query({'code': 'product_ub'}),
        analyt_metadata=an_prod_2
    )
    h.add_node(od_pchod_prub)

    od_pchod_prub_ratio = MetricNode(
        id=170,
        code='od_pchod_prub_ratio',
        name='Тариф',
        parent=od_pchod_prub.id,
        componentMultiPartType=ComponentMultiPartType.RATE
    )
    h.add_node(od_pchod_prub_ratio)

    od_pchod_prub_base = MetricNode(
        id=180,
        code='od_pchod_prub_base',
        name='Количество продаж',
        parent=od_pchod_prub.id,
        componentMultiPartType=ComponentMultiPartType.BASE,
        query=Query({'code': 'cnt_sales_bsp', 'kpi_name': 'Продукты УБ'})
    )
    h.add_node(od_pchod_prub_base)

    od_pchod_brok = MetricNode(
        id=190,
        code='od_pchod_brok',
        name='Брокерское обслуживание',
        parent=od_pchod.id,
        query=Query({'code': 'PL_16_54_35'}),
        analyt_metadata=an_tb

    )
    h.add_node(od_pchod_brok)

    od_pchod_compfundcash = MetricNode(
        id=200,
        code='od_pchod_compfundcash',
        name='Компенсация фондирования ДС',
        parent=od_pchod.id,
        query=Query({'code': 'PL_11_38_34'}),
        analyt_metadata=an_tb

    )
    h.add_node(od_pchod_compfundcash)

    od_pchod_comprlest = MetricNode(
        id=210,
        code='od_pchod_comprlest',
        name='Компенсация по недвижимости',
        parent=od_pchod.id,
        query=Query({'code': 'PL_16_55_02'}),
        analyt_metadata=an_tb

    )
    h.add_node(od_pchod_comprlest)

    od_pchod_salsoc = MetricNode(
        id=220,
        code='od_pchod_salsoc',
        name='Зарплатные проекты и соц. зачисления',
        parent=od_pchod.id,
        query=Query({'code': 'sal_soc'}),
        analyt_metadata=an_tb

    )
    h.add_node(od_pchod_salsoc)

    od_pchod_su = MetricNode(
        id=240,
        code='od_pchod_su',
        name='Расчёты за устройства самообслуживания',
        parent=od_pchod.id,
        type=MetricType.SUM,
    )
    h.add_node(od_pchod_su)

    od_pchod_su_cash = MetricNode(
        id=250,
        code='od_pchod_su_cash',
        name='Взнос/выдача наличных',
        parent=od_pchod_su.id,
        query=Query({'code': 'PL_08_38_47'}),
        analyt_metadata=an_tb,
    )
    h.add_node(od_pchod_su_cash)

    od_pchod_su_compusf = MetricNode(
        id=260,
        code='od_pchod_su_compusf',
        name='Компенсация УС СФ',
        parent=od_pchod_su.id,
        query=Query({'code': 'PL_08_39_03'}),
        analyt_metadata=an_tb,
    )
    h.add_node(od_pchod_su_compusf)

    od_pchod_su_selfcash = MetricNode(
        id=270,
        code='od_pchod_su_selfcash',
        name='Самоинкассация',
        parent=od_pchod_su.id,
        query=Query({'code': 'PL_08_39_38'}),
        analyt_metadata=an_tb,
    )
    h.add_node(od_pchod_su_selfcash)

    od_pchod_oth = MetricNode(
        id=230,
        code='od_pchod_oth',
        name='Прочее',
        parent=od_pchod.id,
        query=Query({'code': 'others'}),
        analyt_metadata=an_tb

    )
    h.add_node(od_pchod_oth)

    print(h.to_json_string())

    return h





def main():
    h = mk_hier()


if __name__ == '__main__':
    main()
















if __name__ == '__main__':
    main()



