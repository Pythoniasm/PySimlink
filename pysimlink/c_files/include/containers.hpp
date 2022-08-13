#pragma once

extern "C"{
#include "rtw_capi.h"
#include "rtw_modelmap.h"
}

#include <string>
#include <vector>

namespace PYSIMLINK{
    class map_key_2s{
    public:
        std::string a;
        std::string b;
        const rtwCAPI_ModelMappingInfo *c;
        bool operator==(const map_key_2s &other) const{
            if(c != other.c) return false;

            return ((a == other.a) && (b == other.b));
        }
    };
    class map_key_1s{
    public:
        std::string a;
        const rtwCAPI_ModelMappingInfo *c;
        bool operator==(const map_key_1s &other) const{
            if(c != other.c) return false;
            return (a == other.a);
        }
    };

    struct pair_hash{
        std::size_t operator()(const map_key_2s &p) const;
        std::size_t operator()(const map_key_1s &p) const;
    };
    struct Compare{
        bool operator()(const map_key_2s &lhs, const map_key_2s &rhs) const;
        bool operator()(const map_key_1s &lhs, const map_key_1s &rhs) const;
    };

    struct DataType{
        std::string cDataType;
        std::string pythonType;
        std::vector<ssize_t> dims;
        rtwCAPI_Orientation orientation;
    };

    struct ModelParam{
        std::string model_param;
        struct DataType data_type;
    };

    struct BlockParam{
        std::string block_name;
        std::string block_param;
        struct DataType data_type;
    };

    struct Signal{
        std::string block_name;
        std::string signal_name;
        struct DataType data_type;
    };

    struct ModelInfo{
        std::string model_name;
        std::vector<struct ModelParam> model_params;
        std::vector<struct BlockParam> block_params;
        std::vector<struct Signal> signals;
    };
};