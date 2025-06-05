<?php


echo "\n";

$parsels = json_decode(file_get_contents('../source/Shennandoah_map_shapes.json'));
$data_tax = json_decode(file_get_contents('../json/Retreat_tax_2025-03-24.json'));
$data_tax = $data_tax->data;
$data_hd = json_decode(file_get_contents('../json/Retreat_hd_2025-03-24.json'));
$data_hd = $data_hd->data;

foreach ($parsels->features as $key => $value) {
$tax_id = $parsels->features[$key]->properties->TAX_MAP;

//Add tax
if(isset($data_tax->$tax_id)){
if($data_tax->$tax_id > 0 ){
$parsels->features[$key]->properties->tax_debt = $data_tax->$tax_id;
}
}

//Add hd
if(isset($data_hd->{$tax_id})){
$i=0;
foreach ($data_hd->{$tax_id} as $hd)
$parsels->features[$key]->properties->{"hd_desc_".($i+1)} = $hd->desc;
$parsels->features[$key]->properties->{"hd_date_".($i+1)} = $hd->date;
$parsels->features[$key]->properties->{"hd_file_".($i+1)} = $hd->file;
$i++;
}

}


file_put_contents("../build/Combo_2025-06-03.json", json_encode($parsels));




?>