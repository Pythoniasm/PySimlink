import glob
import os
import re
import sys
from typing import Union
import zipfile

from pysimlink.utils import annotation_utils as anno
from pysimlink.utils.model_utils import get_other_in_dir


class ModelPaths:
    """
    Holds information about the paths to the model being built.
    """

    root_dir: str  ## Directory containing all model components.
    simulink_native: str  ## path to the directory containing stuff
    #  generated by simulink for every model
    root_model_path: str  ## Path to the root model
    root_model_name: str  ## Name of the root model
    compile_type: str  ## grt, ert, etc...
    suffix: str  ## Suffix added to the model name. Usually 'rtw'
    has_references: bool  ## If this model contains references
    models_dir: str  ## directory containing all simulink code related to the models
    slprj_dir: Union[str, None]  ## Directory will all child models (contains compile_type)
    tmp_dir: str ## Directory where all compiled models will be built

    def __init__(
        self,
        root_dir: str,
        model_name: str,
        compile_type: str = "grt",
        suffix: str = "rtw",
        tmp_dir: "Union[str, None]" = None,
    ):
        """
        Args:
            root_dir: Directory created during codegen. Should have two directories in it.
            model_name: Name of the root model.
            compile_type: grt, ert, etc...
            suffix: the suffix added to the model name directory. usually 'rtw'
            tmp_dir: Where to store the build files. Defaults to __pycache__
        """
        self.compile_type = compile_type
        if self.compile_type != "grt":
            raise ValueError(
                "Unsupported compile target. grt is the only supported simulink "
                "code generation target.\nChange your code generation settings "
                "to use the grt.tlc target and try again. (compile_type should "
                f"be `grt` not {self.compile_type})"
            )
        self.suffix = suffix
        zip_test = os.path.splitext(root_dir)
        if zip_test[-1] == ".zip":
            with zipfile.ZipFile(root_dir, "r") as f:
                if tmp_dir is None:
                    ext_dir = os.path.join(
                        os.path.dirname(sys.argv[0]),
                        "__pycache__",
                        "extract",
                        os.path.basename(zip_test[0]),
                    )
                f.extractall(ext_dir)
            self.root_dir = ext_dir
        else:
            self.root_dir = root_dir

        walk = os.walk(self.root_dir, followlinks=False)
        for (cur_path, folders, _) in walk:
            if "simulink" in folders:
                self.simulink_native = cur_path
                break
        else:
            raise RuntimeError(f"{self.root_dir} is not a valid simulink model.")

        models_dir = get_other_in_dir(self.root_dir, os.path.basename(self.simulink_native))
        self.models_dir = os.path.join(self.root_dir, models_dir)

        self.has_references = os.path.exists(os.path.join(self.models_dir, "slprj"))

        self.root_model_path = os.path.join(
            self.models_dir, model_name + "_" + compile_type + "_" + suffix
        )
        if not os.path.exists(self.root_model_path):
            try:
                model_name = model_name.split("_" + compile_type + "_" + suffix)[0]
            except:  # pylint: disable=W0702
                pass
            self.root_model_path = os.path.join(
                self.models_dir, model_name + "_" + compile_type + "_" + suffix
            )
            if not os.path.exists(self.root_model_path):
                raise RuntimeError(
                    f"Cannot find folder with name '{model_name}' in '{self.models_dir}'"
                )
        self.root_model_name = model_name
        if self.has_references:
            self.slprj_dir = os.path.join(self.models_dir, "slprj", compile_type)

        if tmp_dir is None:
            self.tmp_dir = os.path.join(
                os.path.dirname(sys.argv[0]),
                "__pycache__",
                "pysimlink",
                self.root_model_name,
            )
        else:
            self.tmp_dir = os.path.join(tmp_dir, model_name)
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.verify_capi()

    def verify_capi(self):
        """
        Make sure that this model was generated with the c api. This doesn't use
        the function in the capi, but we need the model mapping interface (mmi).
        """
        files = glob.glob(self.root_model_path + "/*.c", recursive=False)
        files = map(os.path.basename, files)
        assert self.root_model_name + "_capi.c" in files, (
            "Model not generated with capi. Enable the following options in the Code Generation model settings: \n"
            "\tGenerate C API for: signals, parameters, states, root-level I/O"
        )

        ## also check that this is not a multitasked model
        with open(
            os.path.join(self.root_model_path, self.root_model_name + ".h"), encoding="utf-8"
        ) as f:
            lines = f.readlines()

        regex = re.compile(
            f"extern void {self.root_model_name}_step\(void\);"  # pylint: disable=W1401
        )
        for line in lines:
            if re.search(regex, line):
                break
        else:
            raise RuntimeError(
                "Model is setup with multitasking. Disable the following options in the Solver settings and recompile: \n"
                "\t- 'Treat each discrete rate as a separate task'\n\t- 'Allow tasks to execute concurrently on target'"
            )

    def compiler_factory(self) -> "anno.Compiler":
        """
        Return the correct compiler. This could be simplified later -or- more
        compilers could be added if we want to use something other than cmake.
        """
        if self.has_references:  # pylint: disable=R1705
            from pysimlink.lib.compilers.model_ref_compiler import (  # pylint: disable=C0415
                ModelRefCompiler,
            )

            return ModelRefCompiler(self)
        else:
            from pysimlink.lib.compilers.one_shot_compiler import (  # pylint: disable=C0415
                NoRefCompiler,
            )

            return NoRefCompiler(self)
