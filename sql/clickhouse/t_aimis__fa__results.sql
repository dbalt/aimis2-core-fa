create table t_aimis__fa__results (
    code String,
    dt date,
    data String,
    summary String
) 
engine = MergeTree()
primary key code
order by code
;