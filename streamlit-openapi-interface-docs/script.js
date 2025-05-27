document.addEventListener('DOMContentLoaded', () => {
    const chapterListElement = document.getElementById('chapter-list');
    const contentElement = document.getElementById('content');
    let currentActiveLink = null;

    // --- INICIO DE LA LÓGICA DE GENERACIÓN DINÁMICA DE CAPÍTULOS ---
    const chapterFileNames = [
        '00_index.md',
        '01_openapi_specification_.md',
        '02_dynamic_form_generation_.md',
        '03_authentication_management_.md',
        '04_streamlit_session_state_.md',
        '05_api_service_.md',
        '06_request___response_data_handling_.md',
        '07_api_response_display_.md',
    ];

    function generateTitleFromFileName(fileName) {
        let title = fileName.replace(/^\d{2,}_/, '').replace(/\.md$/, '');
        title = title.replace(/_/g, ' ');
        title = title.split(' ')
                     .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
                     .join(' ');
        title = title.trim();
        return title;
    }

    const chapters = chapterFileNames.map((fileName, index) => {
        const title = generateTitleFromFileName(fileName);
        let displayTitle = title;

        if (fileName === '00_index.md' || fileName === 'index.md') {
            displayTitle = 'Home / Overview';
        } else {
            const chapterNumberFromName = fileName.match(/^\d{2,}/);
            if (chapterNumberFromName) {
                displayTitle = `${parseInt(chapterNumberFromName[0], 10)}. ${title}`;
            } else {
                displayTitle = `${index}. ${title}`;
            }
        }
        if (index === 0 && displayTitle === 'Home / Overview') {
            // Correct title, do nothing
        } else if (displayTitle === 'Home / Overview' && index !== 0) {
             // If 'Home / Overview' is not the first item, give it a number
            const chapterNumberFromName = fileName.match(/^\d{2,}/);
            if (chapterNumberFromName) {
                displayTitle = `${parseInt(chapterNumberFromName[0], 10)}. ${title}`;
            } else {
                 displayTitle = `${index}. ${title}`;
            }
        }


        return {
            file: `chapters/${fileName}`,
            title: displayTitle,
            originalFileName: fileName
        };
    });
    // --- FIN DE LA LÓGICA DE GENERACIÓN DINÁMICA DE CAPÍTULOS ---

    // --- INICIALIZACIÓN DE LIBRERÍAS ---
    try {
        if (typeof mermaid !== 'undefined') {
            mermaid.initialize({ startOnLoad: false, theme: 'dark' });
            console.log("Mermaid initialized.");
        } else {
            console.error("Mermaid library is not loaded.");
        }
    } catch (e) {
        console.error("Error initializing Mermaid:", e);
    }

    if (typeof marked === 'undefined') {
        console.error("Marked.js library is not loaded. Markdown parsing will fail.");
    }
    if (typeof hljs === 'undefined') {
        console.error("Highlight.js library is not loaded. Code highlighting will fail.");
    }
    // --- FIN INICIALIZACIÓN DE LIBRERÍAS ---

    // --- DEFINICIÓN DE FUNCIONES ---
    async function loadChapter(chapterFile, linkElement) {
        try {
            let response = await fetch(chapterFile, { cache: 'reload' });

            if (response.status === 304) {
                response = await fetch(`${chapterFile}?v=${Date.now()}`);
            }

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status} for ${chapterFile}`);
            }

            const markdownText = await response.text();

            if (markdownText.trim() === "") {
                console.warn(`Markdown file ${chapterFile} is empty or contains only whitespace.`);
                contentElement.innerHTML = `<p>The content for this chapter (${chapterFile.split('/').pop()}) appears to be empty.</p>`;
                updateActiveLink(linkElement);
                return;
            }

            let htmlContent = '';
            try {
                if (typeof marked !== 'undefined') {
                    htmlContent = marked.parse(markdownText);
                } else {
                    console.error("Marked.js is not available. Cannot parse Markdown.");
                    htmlContent = `<p style="color:red;">Error: Marked.js library not loaded. Cannot display content.</p><pre>${markdownText.replace(/</g, "<").replace(/>/g, ">")}</pre>`;
                }
            } catch (e) {
                console.error("Error during marked.parse:", e);
                contentElement.innerHTML = `<p style="color:red;">Error parsing Markdown for ${chapterFile.split('/').pop()}: ${e.message}</p>`;
                updateActiveLink(linkElement);
                return;
            }

            if (htmlContent.trim() === "" && markdownText.trim() !== "") {
                console.warn(`HTML content is empty after parsing non-empty markdown file: ${chapterFile}.`);
                contentElement.innerHTML = `<p>Content parsed to empty HTML for ${chapterFile.split('/').pop()}.</p>`;
                updateActiveLink(linkElement);
                return;
            }

            contentElement.innerHTML = htmlContent;

            // --- MANEJO DE ENLACES INTERNOS DEL CONTENIDO (NUEVO) ---
            contentElement.querySelectorAll('a').forEach(contentLink => {
                const href = contentLink.getAttribute('href');
                if (href && href.endsWith('.md')) {
                    const fileNameOnly = href.split('/').pop();
                    const targetChapter = chapters.find(ch => ch.originalFileName === fileNameOnly);
                    
                    if (targetChapter) {
                        contentLink.addEventListener('click', (e) => {
                            e.preventDefault();
                            const safeFileName = targetChapter.originalFileName.replace(/\.md$/, '').replace(/[^a-zA-Z0-9_-]/g, '');
                            window.location.hash = `#${safeFileName}`;
                        });
                    } else {
                        // Potentially an external .md link or one not in our list
                        // For now, let it behave as a normal link or open in new tab if external
                        if (!href.startsWith('#') && (href.startsWith('http://') || href.startsWith('https://'))) {
                            contentLink.setAttribute('target', '_blank');
                            contentLink.setAttribute('rel', 'noopener noreferrer');
                        }
                    }
                } else if (href && !href.startsWith('#') && (href.startsWith('http://') || href.startsWith('https://'))) {
                     contentLink.setAttribute('target', '_blank');
                     contentLink.setAttribute('rel', 'noopener noreferrer');
                }
            });
            // --- FIN DEL MANEJO DE ENLACES INTERNOS ---

            if (typeof mermaid !== 'undefined') {
                const mermaidElements = contentElement.querySelectorAll('div.mermaid, pre > code.language-mermaid');
                if (mermaidElements.length > 0) {
                    mermaidElements.forEach(el => {
                        if (el.tagName === 'CODE' && el.parentElement.tagName === 'PRE' && el.classList.contains('language-mermaid')) {
                            const diagramDefinition = el.textContent;
                            const tempDiv = document.createElement('div');
                            tempDiv.className = 'mermaid';
                            tempDiv.textContent = diagramDefinition;
                            const preElement = el.parentElement;
                            preElement.parentElement.replaceChild(tempDiv, preElement);
                        }
                    });
                    const actualMermaidDivs = Array.from(contentElement.querySelectorAll('div.mermaid')).filter(div => !div.hasAttribute('data-processed'));
                    if (actualMermaidDivs.length > 0) {
                        await mermaid.run({ nodes: actualMermaidDivs });
                    }
                }
            }

            if (typeof hljs !== 'undefined') {
                contentElement.querySelectorAll('pre code:not(.language-mermaid)').forEach((block) => {
                    if (!block.parentElement.classList.contains('mermaid')) {
                        hljs.highlightElement(block);
                    }
                });
            }

            updateActiveLink(linkElement); // linkElement es el del sidebar
            contentElement.scrollTop = 0;

        } catch (error) {
            contentElement.innerHTML = `<p style="color:red;">Error loading chapter ${chapterFile.split('/').pop()}: ${error.message}</p>`;
            console.error(`Error loading chapter ${chapterFile}:`, error);
            updateActiveLink(linkElement);
        }
    }

    function updateActiveLink(linkElement) {
        if (currentActiveLink) {
            currentActiveLink.classList.remove('active');
        }
        if (linkElement) {
            linkElement.classList.add('active');
            currentActiveLink = linkElement;
        }
    }

    function buildChapterNavigation() {
        if (chapterListElement) {
            chapters.forEach(chapter => {
                const listItem = document.createElement('li');
                const link = document.createElement('a');
                const safeFileName = chapter.originalFileName.replace(/\.md$/, '').replace(/[^a-zA-Z0-9_-]/g, '');
                link.href = `#${safeFileName}`;
                link.textContent = chapter.title;
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    if (window.location.hash !== link.hash) {
                        window.location.hash = link.hash;
                    } else {
                        loadChapter(chapter.file, link); // Forzar recarga si se hace clic en el mismo enlace
                    }
                });
                listItem.appendChild(link);
                chapterListElement.appendChild(listItem);
            });
        } else {
            console.error("Sidebar element #chapter-list not found.");
        }
    }

    function loadInitialChapter() {
        const hash = window.location.hash.substring(1);
        let chapterToLoad = chapters.length > 0 ? chapters[0] : null;
        let linkToActivate = chapterListElement ? chapterListElement.querySelector('a') : null;

        if (hash && chapterListElement && chapters.length > 0) {
            const foundChapter = chapters.find(c => {
                const safeFileName = c.originalFileName.replace(/\.md$/, '').replace(/[^a-zA-Z0-9_-]/g, '');
                return safeFileName === hash;
            });
            if (foundChapter) {
                chapterToLoad = foundChapter;
                // Encontrar el enlace correspondiente en el sidebar para activar
                const links = chapterListElement.querySelectorAll('a');
                for (let sidebarLink of links) { // Renombrado a sidebarLink para claridad
                    if (sidebarLink.getAttribute('href') === `#${hash}`) {
                        linkToActivate = sidebarLink;
                        break;
                    }
                }
            }
        }
        
        if (chapterToLoad && chapterToLoad.file) {
            loadChapter(chapterToLoad.file, linkToActivate);
        } else if (chapters.length > 0 && chapters[0].file) {
            loadChapter(chapters[0].file, linkToActivate);
        } else {
            console.error("No chapters defined or default chapter is invalid.");
            if(contentElement) contentElement.innerHTML = "<p>No content to display. Please define chapters.</p>";
        }
    }
    // --- FIN DEFINICIÓN DE FUNCIONES ---

    // --- EJECUCIÓN AL CARGAR EL DOM ---
    buildChapterNavigation();

    if (chapters.length > 0) {
        loadInitialChapter();
    } else {
        console.error("No chapters are defined based on chapterFileNames array.");
        if(contentElement) contentElement.innerHTML = "<p>No documentation chapters configured.</p>";
    }
    window.addEventListener('hashchange', loadInitialChapter, false);
    // --- FIN EJECUCIÓN ---

}); // Fin de DOMContentLoaded