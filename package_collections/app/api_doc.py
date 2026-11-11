from flask_restx import fields 
pakage_collections_fields={"id": fields.Integer,
 "pakage_id": fields.Integer,
 "product_id": fields.Integer,
  "is_package_material":fields.Boolean,
 "needded_count": fields.String
 }
search_filters={'id':{
 "type":int,
 "description": "Search by masterId"
},
'product_id':{
 "type":int,
 "description": "Search by product_id"
},
'pakage_id':{
 "type":int,
 "description": "Search by pakage_id"
},
'is_package_material':{
 "type":bool,
 "description": "Search by is_package_material"
}

}