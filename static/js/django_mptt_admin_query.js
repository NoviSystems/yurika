
//import "jqtree";
//import Spinner from "spin";

function initTree($tree, autoopen, autoescape, rtl) {
    let error_node = null;

    function createLi(node, $li) {
        // Create edit link
        const $title = $li.find(".jqtree-title");
        $title.before(
            `<input type="checkbox" name="${node.id}-add" value="True" />`
        );
        if(node.regex) {                                                          
            $title.after(
                ` : ${node.regex}`
            );  
        }
    }

    function handleLoadFailed() {
        $tree.html("Error while loading the data from the server");
    }

    const spinners = {};

    function handleLoading(is_loading, node, $el) {
        function getNodeId() {
            if (!node) {
                return "__root__";
            }
            else {
                return node.id;
            }
        }

        function getContainer() {
            if (node) {
                return $el.find(".jqtree-element")[0];
            }
            else {
                return $el[0];
            }
        }

        const node_id = getNodeId();
        if (is_loading) {
            spinners[node_id] = new Spinner().spin(getContainer());
        }
        else {
            const spinner = spinners[node_id];

            if (spinner) {
                spinner.stop();
                spinners[node_id] = null;
            }
        }
    }

    $tree.tree({
        autoOpen: autoopen,
        autoEscape: autoescape,
        buttonLeft: rtl,
        dragAndDrop: false,
        use_context_menu: false,
        onCreateLi: createLi,
        onLoadFailed: handleLoadFailed,
        closedIcon: rtl ? "&#x25c0;" : "&#x25ba;",
        onLoading: handleLoading
    });

}

jQuery(() => {
    const $tree = jQuery("#tree");
    const autoopen = true;
    const autoescape = true;
    const rtl = false;

    initTree($tree, autoopen, autoescape, rtl);
});
