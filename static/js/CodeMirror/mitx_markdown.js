var schematic_height = 300;
var schematic_width = 500;

$(function(){
  $(document).ready(function() {
	  $("a[rel*=leanModal]").leanModal();
    
    $("body").append('<div id="circuit_editor" class="leanModal_box" style="z-index: 11000; left: 50%; margin-left: -250px; position: absolute; top: 100px; opacity: 1; "><div align="center">'+
      '<input class="schematic" height="' + schematic_height + '" width="' + schematic_width + '" id="schematic_editor" name="schematic" type="hidden" value=""/>' + 
      '<button type="button" id="circuit_save_btn">save</button></div></div>');
    
    //This is the editor that pops up as a modal
    var editorCircuit = $("#schematic_editor").get(0);
    //This is the circuit that they last clicked. The one being edited.
    var editingCircuit = null;
    //Notice we use live, because new circuits can be inserted  
    $(".schematic_open").live("click", function() {
      //Find the new editingCircuit. Transfer its contents to the editorCircuit
      editingCircuit = $(this).children("input.schematic").get(0);
        
      editingCircuit.schematic.update_value();
      var circuit_so_far = $(editingCircuit).val();
        
	    var n = editorCircuit.schematic.components.length;
	    for (var i = 0; i < n; i++)
		    editorCircuit.schematic.components[n - 1 - i].remove();
        
      editorCircuit.schematic.load_schematic(circuit_so_far, "");
    });
    
    $("#circuit_save_btn").click(function () {
      //Take the circuit from the editor and put it back into editingCircuit 
      editorCircuit.schematic.update_value();
      var saving_circuit = $(editorCircuit).val();
        
	    var n = editingCircuit.schematic.components.length;
	    for (var i = 0; i < n; i++)
		    editingCircuit.schematic.components[n - 1 - i].remove();
        
      editingCircuit.schematic.load_schematic(saving_circuit, "");
      
      if (editingCircuit.codeMirrorLine) {
        editingCircuit.codeMirrorLine.replace(0, null, "circuit-schematic:" + saving_circuit);
      }
      
      $(".modal_close").first().click();
    });
  });
});


CodeMirror.defineMode("mitx_markdown", function(cmCfg, modeCfg) {

  var htmlMode = CodeMirror.getMode(cmCfg, { name: 'xml', htmlMode: true });

  var header   = 'header'
  ,   code     = 'comment'
  ,   quote    = 'quote'
  ,   list     = 'string'
  ,   hr       = 'hr'
  ,   linktext = 'link'
  ,   linkhref = 'string'
  ,   em       = 'em'
  ,   strong   = 'strong'
  ,   emstrong = 'emstrong';
  
  function escapeHtml(unsafe) {
      return unsafe
           .replace(/&/g, "&amp;")
           .replace(/</g, "&lt;")
           .replace(/>/g, "&gt;")
           .replace(/"/g, "&quot;")
           .replace(/'/g, "&#039;");
   }
   
   var circuit_formatter = {
     creator: function(text) {
       var circuit_value = text.match(circuitRE)[1]
      
       circuit_value = escapeHtml(circuit_value);
      
       var html = "<div style='display:block;line-height:0;' class='schematic_container'><a href='#circuit_editor' rel='leanModal' class='schematic_open' style='display:inline-block;'>" + 
                   "<input type='hidden' parts='' value='" + circuit_value + "' width='" + schematic_width + "' height='" + schematic_height + "' analyses='' class='schematic ctrls'/></a></div>";
                   
       return html;
     },
     size: function(text) {
       return {width: schematic_width, height:schematic_height};
     },
     callback: function(node, line) {
       update_schematics();
       var schmInput = node.firstChild.firstChild;
       schmInput.codeMirrorLine = line;
       if (schmInput.schematic) { //This is undefined if there was an error making the schematic
         schmInput.schematic.canvas.style.display = "block"; //Otherwise, it gets line height and is a weird size
         schmInput.schematic.always_draw_grid = true;
         schmInput.schematic.redraw_background();
       }
       $(node.firstChild).leanModal();
     }
   };
   

  var hrRE = /^[*-=_]/
  ,   ulRE = /^[*-+]\s+/
  ,   olRE = /^[0-9]+\.\s+/
  ,   headerRE = /^(?:\={3,}|-{3,})$/
  ,   codeRE = /^(k:\t|\s{4,})/
  ,   textRE = /^[^\[*_\\<>`]+/
  ,   circuitRE = /^circuit-schematic:(.*)$/;

  function switchInline(stream, state, f) {
    state.f = state.inline = f;
    return f(stream, state);
  }

  function switchBlock(stream, state, f) {
    state.f = state.block = f;
    return f(stream, state);
  }


  // Blocks

  function blockNormal(stream, state) {
    var match;
    if (stream.match(circuitRE)) {
      stream.skipToEnd();
      return circuit_formatter;
    } else if (stream.match(codeRE)) {
      stream.skipToEnd();
      return code;
    } else if (stream.eatSpace()) {
      return null;
    } else if (stream.peek() === '#' || stream.match(headerRE)) {
      state.header = true;
    } else if (stream.eat('>')) {
      state.indentation++;
      state.quote = true;
    } else if (stream.peek() === '[') {
      return switchInline(stream, state, footnoteLink);
    } else if (hrRE.test(stream.peek())) {
      var re = new RegExp('(?:\s*['+stream.peek()+']){3,}$');
      if (stream.match(re, true)) {
        return hr;
      }
    } else if (match = stream.match(ulRE, true) || stream.match(olRE, true)) {
      state.indentation += match[0].length;
      return list;
    }
    
    return switchInline(stream, state, state.inline);
  }

  function htmlBlock(stream, state) {
    var style = htmlMode.token(stream, state.htmlState);
    if (style === 'tag' && state.htmlState.type !== 'openTag' && !state.htmlState.context) {
      state.f = inlineNormal;
      state.block = blockNormal;
    }
    return style;
  }


  // Inline
  function getType(state) {
    
    // Set defaults
    returnValue = '';
    
    // Strong / Emphasis
    if(state.strong){
      if(state.em){
        returnValue += (returnValue ? ' ' : '') + emstrong;
      } else {
        returnValue += (returnValue ? ' ' : '') + strong;
      }
    } else {
      if(state.em){
        returnValue += (returnValue ? ' ' : '') + em;
      }
    }
    
    // Header
    if(state.header){
      returnValue += (returnValue ? ' ' : '') + header;
    }
    
    // Quotes
    if(state.quote){
      returnValue += (returnValue ? ' ' : '') + quote;
    }
    
    // Check valud and return
    if(!returnValue){
      returnValue = null;
    }
    return returnValue;
    
  }

  function handleText(stream, state) {
    if (stream.match(textRE, true)) {
      return getType(state);
    }
    return undefined;        
  }

  function inlineNormal(stream, state) {
    var style = state.text(stream, state)
    if (typeof style !== 'undefined')
      return style;
    
    var ch = stream.next();
    
    if (ch === '\\') {
      stream.next();
      return getType(state);
    }
    if (ch === '`') {
      return switchInline(stream, state, inlineElement(code, '`'));
    }
    if (ch === '[') {
      return switchInline(stream, state, linkText);
    }
    if (ch === '<' && stream.match(/^\w/, false)) {
      stream.backUp(1);
      return switchBlock(stream, state, htmlBlock);
    }

    var t = getType(state);
    if (ch === '*' || ch === '_') {
      if (stream.eat(ch)) {
        return (state.strong = !state.strong) ? getType(state) : t;
      }
      return (state.em = !state.em) ? getType(state) : t;
    }
    
    return getType(state);
  }

  function linkText(stream, state) {
    while (!stream.eol()) {
      var ch = stream.next();
      if (ch === '\\') stream.next();
      if (ch === ']') {
        state.inline = state.f = linkHref;
        return linktext;
      }
    }
    return linktext;
  }

  function linkHref(stream, state) {
    stream.eatSpace();
    var ch = stream.next();
    if (ch === '(' || ch === '[') {
      return switchInline(stream, state, inlineElement(linkhref, ch === '(' ? ')' : ']'));
    }
    return 'error';
  }

  function footnoteLink(stream, state) {
    if (stream.match(/^[^\]]*\]:/, true)) {
      state.f = footnoteUrl;
      return linktext;
    }
    return switchInline(stream, state, inlineNormal);
  }

  function footnoteUrl(stream, state) {
    stream.eatSpace();
    stream.match(/^[^\s]+/, true);
    state.f = state.inline = inlineNormal;
    return linkhref;
  }

  function inlineRE(endChar) {
    if (!inlineRE[endChar]) {
      // match any not-escaped-non-endChar and any escaped char
      // then match endChar or eol
      inlineRE[endChar] = new RegExp('^(?:[^\\\\\\' + endChar + ']|\\\\.)*(?:\\' + endChar + '|$)');
    }
    return inlineRE[endChar];
  }

  function inlineElement(type, endChar, next) {
    next = next || inlineNormal;
    return function(stream, state) {
      stream.match(inlineRE(endChar));
      state.inline = state.f = next;
      return type;
    };
  }

  return {
    startState: function() {
      return {
        f: blockNormal,
        
        block: blockNormal,
        htmlState: htmlMode.startState(),
        indentation: 0,
        
        inline: inlineNormal,
        text: handleText,
        em: false,
        strong: false,
        header: false,
        quote: false
      };
    },

    copyState: function(s) {
      return {
        f: s.f,
        
        block: s.block,
        htmlState: CodeMirror.copyState(htmlMode, s.htmlState),
        indentation: s.indentation,
        
        inline: s.inline,
        text: s.text,
        em: s.em,
        strong: s.strong,
        header: s.header,
        quote: s.quote
      };
    },

    token: function(stream, state) {
      if (stream.sol()) {
        // Reset EM state
        state.em = false;
        // Reset STRONG state
        state.strong = false;
        // Reset state.header
        state.header = false;
        // Reset state.quote
        state.quote = false;

        state.f = state.block;
        var previousIndentation = state.indentation
        ,   currentIndentation = 0;
        while (previousIndentation > 0) {
          if (stream.eat(' ')) {
            previousIndentation--;
            currentIndentation++;
          } else if (previousIndentation >= 4 && stream.eat('\t')) {
            previousIndentation -= 4;
            currentIndentation += 4;
          } else {
            break;
          }
        }
        state.indentation = currentIndentation;
        
        if (currentIndentation > 0) return null;
      }
      return state.f(stream, state);
    },

    getType: getType
  };

});

CodeMirror.defineMIME("text/x-markdown", "markdown");
