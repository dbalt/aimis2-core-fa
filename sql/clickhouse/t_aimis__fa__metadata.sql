create table missa_aimis.t_aimis__fa__metadata (
    code String,     
    metadata String
) 
engine = MergeTree()
primary key code
order by code;