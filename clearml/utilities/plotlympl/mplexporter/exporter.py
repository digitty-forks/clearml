"""
Matplotlib Exporter
===================
This submodule contains tools for crawling a matplotlib figure and exporting
relevant pieces to a renderer.
"""
import io
import warnings
from typing import Tuple, Union, Any

import matplotlib
import numpy
from matplotlib import transforms, collections  # noqa: F401
from matplotlib.backends.backend_agg import FigureCanvasAgg

from . import utils


class Exporter(object):
    """Matplotlib Exporter

    Parameters
    ----------
    renderer : Renderer object
        The renderer object called by the exporter to create a figure
        visualization.  See mplexporter.Renderer for information on the
        methods which should be defined within the renderer.
    close_mpl : bool
        If True (default), close the matplotlib figure as it is rendered. This
        is useful for when the exporter is used within the notebook, or with
        an interactive matplotlib backend.
    """

    def __init__(self, renderer: Any, close_mpl: bool = True) -> None:
        self.close_mpl = close_mpl
        self.renderer = renderer
        self.has_legend = False
        self.legend_as_annotation = True

    def run(self, fig: Any, show_legend: bool = True) -> None:
        """
        Run the exporter on the given figure

        Parmeters
        ---------
        fig : matplotlib.Figure instance
            The figure to export

        show_legend: If True, plotly show legend if plt has one, If False add legend as annotations on plot.
        """
        # Calling savefig executes the draw() command, putting elements
        # in the correct place.
        self.legend_as_annotation = not show_legend
        if fig.canvas is None:
            canvas = FigureCanvasAgg(fig)  # noqa: F841
        fig.savefig(io.BytesIO(), format="png", dpi=fig.dpi)
        if self.close_mpl:
            import matplotlib.pyplot as plt

            plt.close(fig)
        self.crawl_fig(fig)
        if show_legend and self.has_legend:
            self.renderer.plotly_fig["layout"]["showlegend"] = True

    @staticmethod
    def process_transform(
        transform: matplotlib.transforms.Transform,
        ax: Any = None,
        data: numpy.ndarray = None,
        return_trans: bool = False,
        force_trans: Any = None,
    ) -> Union[Tuple[str, numpy.ndarray, Any], Tuple[str, numpy.ndarray], Tuple[str, Any], str]:
        """Process the transform and convert data to figure or data coordinates

        Parameters
        ----------
        transform : matplotlib Transform object
            The transform applied to the data
        ax : matplotlib Axes object (optional)
            The axes the data is associated with
        data : ndarray (optional)
            The array of data to be transformed.
        return_trans : bool (optional)
            If true, return the final transform of the data
        force_trans : matplotlib.transform instance (optional)
            If supplied, first force the data to this transform

        Returns
        -------
        code : string
            Code is either "data", "axes", "figure", or "display", indicating
            the type of coordinates output.
        transform : matplotlib transform
            the transform used to map input data to output data.
            Returned only if return_trans is True
        new_data : ndarray
            Data transformed to match the given coordinate code.
            Returned only if data is specified
        """
        if isinstance(transform, transforms.BlendedGenericTransform):
            warnings.warn("Blended transforms not yet supported. Zoom behavior may not work as expected.")

        if force_trans is not None:
            if data is not None:
                data = (transform - force_trans).transform(data)
            transform = force_trans

        code = "display"
        if ax is not None:
            for c, trans in [
                ("data", ax.transData),
                ("axes", ax.transAxes),
                ("figure", ax.figure.transFigure),
                ("display", transforms.IdentityTransform()),
            ]:
                if transform.contains_branch(trans):
                    code, transform = (c, transform - trans)
                    break

        if data is not None:
            if return_trans:
                return code, transform.transform(data), transform
            else:
                return code, transform.transform(data)
        else:
            if return_trans:
                return code, transform
            else:
                return code

    def crawl_fig(self, fig: Any) -> None:
        """Crawl the figure and process all axes"""
        with self.renderer.draw_figure(fig=fig, props=utils.get_figure_properties(fig)):
            for ax in fig.axes:
                self.crawl_ax(ax)

    def crawl_ax(self, ax: Any) -> None:
        """Crawl the axes and process all elements within"""
        with self.renderer.draw_axes(ax=ax, props=utils.get_axes_properties(ax)):
            for line in ax.lines:
                self.draw_line(ax, line)
            for text in ax.texts:
                self.draw_text(ax, text)
            for text, ttp in zip(
                [ax.xaxis.label, ax.yaxis.label, ax.title] + ([ax.zaxis.label] if hasattr(ax, "zaxis") else []),
                ["xlabel", "ylabel", "title"] + (["zlabel"] if hasattr(ax, "zaxis") else []),
            ):
                if hasattr(text, "get_text") and text.get_text():
                    self.draw_text(ax, text, force_trans=ax.transAxes, text_type=ttp)
            for artist in ax.artists:
                # TODO: process other artists
                if isinstance(artist, matplotlib.text.Text):
                    self.draw_text(ax, artist)
            for patch in ax.patches:
                self.draw_patch(ax, patch)
            for collection in ax.collections:
                self.draw_collection(ax, collection)
            for image in ax.images:
                self.draw_image(ax, image)

            legend = ax.get_legend()
            if legend is not None:
                self.has_legend = True
                if self.legend_as_annotation:
                    props = utils.get_legend_properties(ax, legend)
                    with self.renderer.draw_legend(legend=legend, props=props):
                        if props["visible"]:
                            self.crawl_legend(ax, legend)

    def crawl_legend(self, ax: Any, legend: Any) -> None:
        """
        Recursively look through objects in legend children
        """
        legendElements = list(utils.iter_all_children(legend._legend_box, skipContainers=True))
        legendElements.append(legend.legendPatch)
        for child in legendElements:
            # force a large zorder so it appears on top
            child.set_zorder(1e6 + child.get_zorder())

            # reorder border box to make sure marks are visible
            if isinstance(child, matplotlib.patches.FancyBboxPatch):
                child.set_zorder(child.get_zorder() - 1)

            try:
                # What kind of object...
                if isinstance(child, matplotlib.patches.Patch):
                    self.draw_patch(ax, child, force_trans=ax.transAxes)
                elif isinstance(child, matplotlib.text.Text):
                    if child.get_text() != "None":
                        self.draw_text(ax, child, force_trans=ax.transAxes)
                elif isinstance(child, matplotlib.lines.Line2D):
                    self.draw_line(ax, child, force_trans=ax.transAxes)
                elif isinstance(child, matplotlib.collections.Collection):
                    self.draw_collection(ax, child, force_pathtrans=ax.transAxes)
                else:
                    warnings.warn("Legend element %s not impemented" % child)
            except NotImplementedError:
                warnings.warn("Legend element %s not impemented" % child)

    def draw_line(
        self,
        ax: Any,
        line: Any,
        force_trans: Any = None,
    ) -> None:
        """Process a matplotlib line and call renderer.draw_line"""
        coordinates, data = self.process_transform(line.get_transform(), ax, line.get_xydata(), force_trans=force_trans)
        linestyle = utils.get_line_style(line)
        if linestyle["dasharray"] is None and linestyle["drawstyle"] == "default":
            linestyle = None
        markerstyle = utils.get_marker_style(line)
        if markerstyle["marker"] in ["None", "none", None] or markerstyle["markerpath"][0].size == 0:
            markerstyle = None
        label = line.get_label()
        if markerstyle or linestyle:
            self.renderer.draw_marked_line(
                data=data,
                coordinates=coordinates,
                linestyle=linestyle,
                markerstyle=markerstyle,
                label=label,
                mplobj=line,
            )

    def draw_text(
        self,
        ax: Any,
        text: Any,
        force_trans: Any = None,
        text_type: str = None,
    ) -> None:
        """Process a matplotlib text object and call renderer.draw_text"""
        content = text.get_text()
        if content:
            transform = text.get_transform()
            position = text.get_position()
            coords, position = self.process_transform(transform, ax, position, force_trans=force_trans)
            style = utils.get_text_style(text)
            self.renderer.draw_text(
                text=content,
                position=position,
                coordinates=coords,
                text_type=text_type,
                style=style,
                mplobj=text,
            )

    def draw_patch(
        self,
        ax: Any,
        patch: Any,
        force_trans: Any = None,
    ) -> None:
        """Process a matplotlib patch object and call renderer.draw_path"""
        vertices, pathcodes = utils.SVG_path(patch.get_path())
        transform = patch.get_transform()
        coordinates, vertices = self.process_transform(transform, ax, vertices, force_trans=force_trans)
        linestyle = utils.get_path_style(patch, fill=patch.get_fill())
        self.renderer.draw_path(
            data=vertices,
            coordinates=coordinates,
            pathcodes=pathcodes,
            style=linestyle,
            mplobj=patch,
        )

    def draw_collection(
        self,
        ax: Any,
        collection: Any,
        force_pathtrans: Any = None,
        force_offsettrans: Any = None,
    ) -> None:
        """Process a matplotlib collection and call renderer.draw_collection"""
        (transform, transOffset, offsets, paths) = collection._prepare_points()
        if hasattr(collection, "_offsets3d"):
            offsets = collection._offsets3d

        offset_coords, offsets = self.process_transform(transOffset, ax, offsets, force_trans=force_offsettrans)
        path_coords = self.process_transform(transform, ax, force_trans=force_pathtrans)

        processed_paths = [utils.SVG_path(path) for path in paths]
        processed_paths = [
            (
                self.process_transform(transform, ax, path[0], force_trans=force_pathtrans)[1],
                path[1],
            )
            for path in processed_paths
        ]

        path_transforms = collection.get_transforms()
        try:
            # matplotlib 1.3: path_transforms are transform objects.
            # Convert them to numpy arrays.
            path_transforms = [t.get_matrix() for t in path_transforms]
        except AttributeError:
            # matplotlib 1.4: path transforms are already numpy arrays.
            pass

        styles = {
            "linewidth": collection.get_linewidths(),
            "facecolor": collection.get_facecolors(),
            "edgecolor": collection.get_edgecolors(),
            "alpha": collection._alpha,
            "zorder": collection.get_zorder(),
        }

        offset_dict = {"data": "before", "screen": "after"}
        # protected for removing  _offset_position() and default to "screen"
        offset_order = offset_dict[getattr(collection, "_offset_position", "screen")]

        self.renderer.draw_path_collection(
            ax,
            paths=processed_paths,
            path_coordinates=path_coords,
            path_transforms=path_transforms,
            offsets=offsets,
            offset_coordinates=offset_coords,
            offset_order=offset_order,
            styles=styles,
            mplobj=collection,
        )

    def draw_image(self, ax: Any, image: Any) -> None:
        """Process a matplotlib image object and call renderer.draw_image"""
        self.renderer.draw_image(
            imdata=utils.image_to_base64(image),
            extent=image.get_extent(),
            coordinates="data",
            style={"alpha": image.get_alpha(), "zorder": image.get_zorder()},
            mplobj=image,
        )
